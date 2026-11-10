#include <algorithm>
#include <array>
#include <bit>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <map>
#include <numeric>
#include <span>
#include <stdexcept>
#include <string>
#include <vector>

using Index = std::uint32_t;
using Money = __uint128_t;
using Currency = std::uint16_t;
using Time = std::int32_t;
using Indices = std::span<const Index>;
constexpr Time day_minutes = 1440;

enum Kind : std::uint8_t { fan_in, fan_out, cycle_2, cycle_3, cycle_4 };
enum Signal : std::uint16_t {
    compact_burst = 1 << 0, related_flow = 1 << 1, enough_history = 1 << 2,
    unusual_fan = 1 << 3, ordered_cycle = 1 << 4, value_continuity = 1 << 5,
    unusual_pair = 1 << 6, wider_flow = 1 << 7
};
enum Method : std::uint8_t {
    baseline, out_flow, out_context, in_flow, in_context, c2_value, c2_context,
    c34_order, c34_value, all_rules, method_count
};

struct Amount {
    std::uint64_t low, high;
    Money exact() const { return (Money(high) << 64) | low; }
};

struct Fact {
    Amount paid, received;
    Index ordinal, sender, receiver;
    Time minute;
    Currency paid_currency, received_currency;
    Index reserved;
};

struct Case {
    Kind kind;
    std::uint8_t day;
    std::uint16_t reserved;
    Index size, degree;
    std::array<Index, 4> nodes;
};

struct Path {
    std::array<Index, 4> payments{};
    std::uint8_t length = 0;
    Index context = 0;
};

struct Result {
    std::uint64_t offset = 0;
    std::uint16_t keep = 0, signals = 0;
    std::uint8_t tier = 0, path_length = 0;
    std::uint16_t reserved = 0;
    std::array<Index, 4> path{};
    Index context = 0, unused = 0;
};

static_assert(sizeof(Fact) == 56 && sizeof(Case) == 28 && sizeof(Result) == 40);

struct GroupedIndex {
    std::vector<Index> payments, offsets;
    Indices for_account(Index node) const {
        return std::span(payments).subspan(offsets[node], offsets[node + 1] - offsets[node]);
    }
};

struct View {
    const std::vector<Fact>& facts;
    const GroupedIndex& out;
    const GroupedIndex& in;
    const GroupedIndex& pairs;
};

struct FanScratch {
    std::vector<Index> degrees, rolling, burst, historical, historical_day;
};

template <class T>
std::vector<T> read_file(const std::filesystem::path& path, std::size_t count) {
    if (std::filesystem::file_size(path) != count * sizeof(T))
        throw std::runtime_error("Unexpected binary input size for " + path.string());
    std::ifstream stream(path, std::ios::binary);
    std::vector<T> data(count);
    if (!stream.read(reinterpret_cast<char*>(data.data()), count * sizeof(T)))
        throw std::runtime_error("Could not read " + path.string());
    return data;
}

template <class T>
void write(std::ofstream& stream, std::span<const T> data) {
    if (!stream.write(reinterpret_cast<const char*>(data.data()), data.size_bytes()))
        throw std::runtime_error("Writing local replay output failed");
}

template <class Key, class Compare>
GroupedIndex make_index(const std::vector<Fact>& facts, Index accounts, Key key, Compare compare) {
    std::vector<Index> offsets(accounts + 1, 0);
    for (const Fact& fact : facts) {
        if (fact.sender >= accounts || fact.receiver >= accounts)
            throw std::runtime_error("Invalid published fact account ID");
        if (fact.sender != fact.receiver) ++offsets[key(fact) + 1];
    }
    std::partial_sum(offsets.begin(), offsets.end(), offsets.begin());
    auto cursor = offsets;
    std::vector<Index> ordered(offsets.back());
    for (Index index = 0; index < facts.size(); ++index) {
        const Fact& fact = facts[index];
        if (fact.sender != fact.receiver) ordered[cursor[key(fact)]++] = index;
    }
    for (Index node = 0; node < accounts; ++node)
        std::sort(ordered.begin() + offsets[node], ordered.begin() + offsets[node + 1], compare);
    return {std::move(ordered), std::move(offsets)};
}

Indices time_range(Indices records, const std::vector<Fact>& facts, Time from, Time until) {
    auto before = [&](Index index, Time minute) { return facts[index].minute < minute; };
    auto first = std::lower_bound(records.begin(), records.end(), from, before);
    return {first, std::lower_bound(first, records.end(), until, before)};
}

Indices pair_records(const View& view, Index source, Index destination) {
    auto records = view.pairs.for_account(source);
    auto first = std::lower_bound(records.begin(), records.end(), destination,
                                  [&](Index index, Index target) { return view.facts[index].receiver < target; });
    auto last = std::upper_bound(first, records.end(), destination,
                                 [&](Index target, Index index) { return target < view.facts[index].receiver; });
    return {first, last};
}

Money within_twenty_percent(Money amount) {
    return 4 * (amount / 5) + (4 * (amount % 5) + 4) / 5;
}

bool comparable(Money a, Money b) {
    Money small = std::min(a, b);
    return small > 0 && small >= within_twenty_percent(std::max(a, b));
}

struct FanDirection {
    const GroupedIndex& primary;
    const GroupedIndex& related;
    Index Fact::*peer;
    Index Fact::*related_peer;
    Amount Fact::*value;
    Amount Fact::*related_value;
    Currency Fact::*currency;
    Currency Fact::*related_currency;
};

struct Burst {
    Indices rows;
    Index peers;
};

Burst largest_burst(Indices rows, const std::vector<Fact>& facts, Index Fact::*peer,
                    std::vector<Index>& counts) {
    Index best_left = 0, best_right = 0, best_peers = 0, distinct = 0, right = 0;
    for (Index left = 0; left < rows.size(); ++left) {
        while (right < rows.size() && facts[rows[right]].minute - facts[rows[left]].minute <= day_minutes)
            distinct += counts[facts[rows[right++]].*peer]++ == 0;
        if (distinct > best_peers) {
            best_left = left;
            best_right = right;
            best_peers = distinct;
        }
        distinct -= --counts[facts[rows[left]].*peer] == 0;
    }
    return {rows.subspan(best_left, best_right - best_left), best_peers};
}

std::uint16_t fan_history(const View& view, const FanDirection& dir, const Burst& burst, Index hub,
                          Index stamp, FanScratch& scratch) {
    const Time first = view.facts[burst.rows.front()].minute;
    const Time from = std::max(Time(0), first - 7 * day_minutes);
    const auto previous = time_range(dir.primary.for_account(hub), view.facts, from, first);
    std::array<Index, 8> counts{};
    for (Index i : previous) {
        const Fact& payment = view.facts[i];
        Index peer = payment.*dir.peer;
        Index day = payment.minute / day_minutes;
        Index marker = (stamp << 5) | day;
        if (scratch.historical_day[peer] != marker) {
            scratch.historical_day[peer] = marker;
            ++counts[day - from / day_minutes];
        }
        scratch.historical[peer] = stamp;
    }
    std::sort(counts.begin(), counts.end());
    auto start = std::upper_bound(counts.begin(), counts.end(), 0);
    auto active = counts.end() - start;
    if (active < 3) return 0;
    Index new_peers = 0;
    for (Index i : burst.rows) {
        Index peer = view.facts[i].*dir.peer;
        if (scratch.historical[peer] != stamp) {
            scratch.historical[peer] = stamp;
            ++new_peers;
        }
    }
    Index double_median = start[active / 2] + start[(active - 1) / 2];
    return enough_history | (5 * new_peers >= 4 * burst.peers || burst.peers >= double_median ? unusual_fan : 0);
}

Index fan_flow(const View& view, const FanDirection& dir, const Burst& burst, Index hub,
               Time from, Time until, Index stamp, const std::vector<Index>& stamped_burst) {
    Money total = 0;
    const Currency currency = view.facts[burst.rows.front()].*dir.currency;
    for (Index i : burst.rows) {
        const Fact& payment = view.facts[i];
        if (payment.*dir.currency != currency) return 0;
        if (__builtin_add_overflow(total, (payment.*dir.value).exact(), &total))
            throw std::overflow_error("Burst exceeds exact monetary accumulation bound");
    }
    for (Index i : time_range(dir.related.for_account(hub), view.facts, from, until)) {
        const Fact& other = view.facts[i];
        if (stamped_burst[other.*dir.related_peer] != stamp && other.*dir.related_currency == currency
                && comparable(total, (other.*dir.related_value).exact()))
            return other.ordinal;
    }
    return 0;
}

using Legs = std::array<Indices, 4>;

Path chronological_path(const View& view, const Legs& legs, unsigned length) {
    for (unsigned rotation = 0; rotation < length; ++rotation) {
        Path path;
        Time next_minute = 0;
        for (unsigned hop = 0; hop < length; ++hop) {
            const auto rows = legs[(rotation + hop) % length];
            auto first = std::lower_bound(rows.begin(), rows.end(), next_minute,
                                          [&](Index i, Time at) { return view.facts[i].minute < at; });
            if (first == rows.end()) break;
            path.payments[path.length++] = *first;
            next_minute = view.facts[*first].minute + 1;
        }
        if (path.length == length) return path;
    }
    return {};
}

using AmountIndex = std::map<std::pair<Currency, Money>, Path>;

void add_receipt(AmountIndex& received, const Fact& fact, Path path) {
    if (fact.received.exact()) received.try_emplace(std::make_pair(fact.received_currency, fact.received.exact()), path);
}

Path matching_receipt(const AmountIndex& received, const Fact& next) {
    const Money paid = next.paid.exact();
    if (!paid) return {};
    auto found = received.lower_bound({next.paid_currency, within_twenty_percent(paid)});
    if (found == received.end() || found->first.first != next.paid_currency
            || !comparable(paid, found->first.second)) return {};
    return found->second;
}

Path value_path(const View& view, const Legs& legs, unsigned length) {
    for (unsigned rotation = 0; rotation < length; ++rotation) {
        std::vector<Path> previous;
        for (Index index : legs[rotation]) previous.push_back({{index}, 1, 0});
        for (unsigned hop = 1; hop < length && !previous.empty(); ++hop) {
            std::vector<Path> reachable;
            AmountIndex received;
            auto cursor = previous.begin();
            for (Index index : legs[(rotation + hop) % length]) {
                const Fact& next = view.facts[index];
                while (cursor != previous.end()) {
                    const Fact& prior = view.facts[cursor->payments[cursor->length - 1]];
                    if (prior.minute >= next.minute) break;
                    add_receipt(received, prior, *cursor++);
                }
                Path path = matching_receipt(received, next);
                if (!path.length) continue;
                path.payments[path.length++] = index;
                if (hop + 1 == length) return path;
                reachable.push_back(path);
            }
            previous = std::move(reachable);
        }
    }
    return {};
}

unsigned active_days(const View& view, Index account, Time from, Time until) {
    std::uint32_t days = 0;
    for (const auto* side : {&view.in, &view.out})
        for (Index i : time_range(side->for_account(account), view.facts, from, until))
            days |= 1U << (view.facts[i].minute / day_minutes);
    return std::popcount(days);
}

bool atypical_pair(const View& view, const Case& item, const Legs& legs, Time cutoff) {
    const Index a = item.nodes[0], b = item.nodes[1];
    const Time first = std::min(view.facts[legs[0].front()].minute, view.facts[legs[1].front()].minute);
    const Time from = std::max(Time(0), first - 7 * day_minutes);
    if (active_days(view, a, from, first) < 3 || active_days(view, b, from, first) < 3) return false;
    const Time end = std::min(cutoff, first + day_minutes);
    std::array<Index, 8> previous{};
    Index current = 0;
    for (const auto direction : {std::pair{a, b}, std::pair{b, a}}) {
        auto bilateral = pair_records(view, direction.first, direction.second);
        for (Index index : time_range(bilateral, view.facts, from, first))
            ++previous[view.facts[index].minute / day_minutes - from / day_minutes];
        current += time_range(bilateral, view.facts, first, end).size();
    }
    return current >= std::max(2U, 2 * *std::max_element(previous.begin(), previous.end()));
}

Index previous_funding(const View& view, const Fact& first) {
    const auto history = time_range(view.in.for_account(first.sender), view.facts,
                                    first.minute - day_minutes, first.minute);
    for (Index index : history) {
        const Fact& external = view.facts[index];
        if (external.sender != first.receiver && external.received_currency == first.paid_currency
                && comparable(external.received.exact(), first.paid.exact()))
            return external.ordinal;
    }
    return 0;
}

Index onward_payment(const View& view, const Fact& last, Time cutoff) {
    const auto next = time_range(view.out.for_account(last.receiver), view.facts,
                                 last.minute + 1, std::min(cutoff, last.minute + day_minutes + 1));
    for (Index index : next) {
        const Fact& external = view.facts[index];
        if (external.receiver != last.sender && last.received_currency == external.paid_currency
                && comparable(last.received.exact(), external.paid.exact()))
            return external.ordinal;
    }
    return 0;
}

Path supported_pair(const View& view, const Legs& legs, Time cutoff) {
    for (unsigned rotation = 0; rotation < 2; ++rotation) {
        const auto previous = legs[rotation];
        auto cursor = previous.begin();
        AmountIndex receipts, funded_receipts;
        for (Index index : legs[1 - rotation]) {
            const Fact& next = view.facts[index];
            while (cursor != previous.end() && view.facts[*cursor].minute < next.minute) {
                const Index first_index = *cursor++;
                const Fact& prior = view.facts[first_index];
                Path first{{first_index}, 1, previous_funding(view, prior)};
                add_receipt(receipts, prior, first);
                if (first.context) add_receipt(funded_receipts, prior, first);
            }
            Path path = matching_receipt(funded_receipts, next);
            if (!path.length) {
                path = matching_receipt(receipts, next);
                if (!path.length) continue;
                path.context = onward_payment(view, next, cutoff);
                if (!path.context) continue;
            }
            path.payments[path.length++] = index;
            return path;
        }
    }
    return {};
}

std::uint16_t keep_mask(Kind kind, std::uint16_t signals) {
    std::uint16_t keep = (1 << method_count) - 1;
    auto require = [&](Method method, std::uint16_t required) {
        if ((signals & required) != required) keep &= ~(1 << method);
    };
    switch (kind) {
        case fan_out:
            require(out_flow, related_flow);
            require(out_context, related_flow | unusual_fan);
            require(all_rules, related_flow | unusual_fan);
            break;
        case fan_in:
            require(in_flow, related_flow);
            require(in_context, related_flow | unusual_fan);
            require(all_rules, related_flow | unusual_fan);
            break;
        case cycle_2:
            require(c2_value, value_continuity);
            if (!(signals & value_continuity) || !(signals & (unusual_pair | wider_flow)))
                keep &= ~((1 << c2_context) | (1 << all_rules));
            break;
        case cycle_3:
        case cycle_4:
            require(c34_order, ordered_cycle);
            require(c34_value, value_continuity);
            require(all_rules, value_continuity);
            break;
    }
    return keep;
}

std::uint8_t rank(Kind kind, std::uint16_t signals, std::uint16_t keep) {
    if (keep & (1 << all_rules)) return 3;
    if (signals & (related_flow | unusual_fan | value_continuity)) return 2;
    if (signals & compact_burst || (kind >= cycle_3 && signals & ordered_cycle)) return 1;
    return 0;
}

void fan(const View& view, const Case& item, Time from, Time cutoff, Index stamp,
         FanScratch& scratch, std::vector<Index>& evidence, Result& result) {
    const FanDirection outward{view.out, view.in, &Fact::receiver, &Fact::sender,
                               &Fact::paid, &Fact::received, &Fact::paid_currency, &Fact::received_currency};
    const FanDirection inward{view.in, view.out, &Fact::sender, &Fact::receiver,
                              &Fact::received, &Fact::paid, &Fact::received_currency, &Fact::paid_currency};
    const auto& dir = item.kind == fan_out ? outward : inward;
    const Index hub = item.nodes[0];
    const auto rows = time_range(dir.primary.for_account(hub), view.facts, from, cutoff);
    Index distinct = 0;
    for (Index index : rows) {
        Index peer = view.facts[index].*dir.peer;
        distinct += scratch.degrees[peer] != stamp;
        scratch.degrees[peer] = stamp;
        evidence.push_back(index);
    }
    if (distinct != item.degree || rows.size() != item.size)
        throw std::runtime_error("A fan case differs from its published topology or evidence count at case " +
                                 std::to_string(stamp));
    const Burst burst = largest_burst(rows, view.facts, dir.peer, scratch.rolling);
    if (burst.peers < 5 || 5 * burst.peers < 4 * distinct) return;
    result.signals |= compact_burst;
    const Time first = view.facts[burst.rows.front()].minute, last = view.facts[burst.rows.back()].minute;
    for (Index index : burst.rows) scratch.burst[view.facts[index].*dir.peer] = stamp;
    const Time context_start = item.kind == fan_out ? first - day_minutes : last + 1;
    const Time context_end = item.kind == fan_out ? first : std::min(cutoff, last + day_minutes + 1);
    result.context = fan_flow(view, dir, burst, hub, context_start, context_end, stamp, scratch.burst);
    if (result.context) result.signals |= related_flow;
    result.signals |= fan_history(view, dir, burst, hub, stamp, scratch);
}

void cycle(const View& view, const Case& item, Time from, Time cutoff,
           std::vector<Index>& evidence, Result& result) {
    const unsigned length = item.degree;
    Legs legs;
    for (unsigned hop = 0; hop < length; ++hop) {
        legs[hop] = time_range(pair_records(view, item.nodes[hop], item.nodes[(hop + 1) % length]),
                               view.facts, from, cutoff);
        if (legs[hop].empty()) throw std::runtime_error("A published cycle edge has no payments");
        evidence.insert(evidence.end(), legs[hop].begin(), legs[hop].end());
    }
    if (evidence.size() != item.size) throw std::runtime_error("A cycle case differs from its published evidence count");
    Path path = chronological_path(view, legs, length);
    if (!path.length) return;
    result.signals |= ordered_cycle;
    Path value = value_path(view, legs, length);
    if (value.length) {
        result.signals |= value_continuity;
        path = value;
        if (length == 2) {
            if (atypical_pair(view, item, legs, cutoff)) {
                result.signals |= unusual_pair;
            } else {
                Path support = supported_pair(view, legs, cutoff);
                if (support.length) {
                    result.signals |= wider_flow;
                    path = support;
                }
            }
        }
    }
    result.path_length = path.length;
    result.context = path.context;
    for (unsigned i = 0; i < path.length; ++i) result.path[i] = view.facts[path.payments[i]].ordinal;
}

unsigned period(unsigned day) {
    return day <= 8 ? 0 : day <= 16 ? 1 : 2;
}

int main(int argc, char** argv) {
    if (argc != 3 && argc != 6)
        throw std::invalid_argument("Usage: replay staging-directory account-count [payments cases memberships]");
    const std::filesystem::path root = argv[1];
    const auto accounts = std::stoul(argv[2]);
    const Index population = argc == 6 ? std::stoul(argv[3]) : 31'898'238;
    const Index expected_cases = argc == 6 ? std::stoul(argv[4]) : 2'251'155;
    const std::uint64_t expected_memberships = argc == 6 ? std::stoull(argv[5]) : 81'321'105;
    if (accounts == 0 || accounts >= std::numeric_limits<Index>::max())
        throw std::invalid_argument("Account count outside the replay format");
    const auto facts = read_file<Fact>(root / "facts.bin", population);
    const auto cases = read_file<Case>(root / "cases.bin", expected_cases);
    std::cerr << "Loaded " << facts.size() << " cleaned payments and " << cases.size() << " detector cases\n";
    auto chronological = [&](Index a, Index b) {
        const Fact& left = facts[a];
        const Fact& right = facts[b];
        return left.minute < right.minute || (left.minute == right.minute && left.ordinal < right.ordinal);
    };
    auto sender = [](const Fact& row) { return row.sender; };
    auto receiver = [](const Fact& row) { return row.receiver; };
    auto target_then_time = [&](Index a, Index b) {
        return facts[a].receiver != facts[b].receiver ? facts[a].receiver < facts[b].receiver : chronological(a, b);
    };
    const auto out = make_index(facts, accounts, sender, chronological);
    const auto in = make_index(facts, accounts, receiver, chronological);
    const auto pairs = make_index(facts, accounts, sender, target_then_time);
    std::cerr << "Built timeline and pair indexes over " << out.payments.size() << " non-self payments\n";
    const View view{facts, out, in, pairs};
    FanScratch scratch{std::vector<Index>(accounts), std::vector<Index>(accounts), std::vector<Index>(accounts),
                       std::vector<Index>(accounts), std::vector<Index>(accounts)};
    std::vector<std::uint16_t> flags(population + 1);
    std::vector<std::uint8_t> motifs(population + 1);
    std::vector<Index> max_fan_out_degree(population + 1), evidence, ordinals;
    std::ofstream payments(root / "evidence.u32", std::ios::binary);
    std::ofstream scored(root / "scored.bin", std::ios::binary);
    if (!payments || !scored) throw std::runtime_error("Could not open replay outputs");
    std::uint64_t offset = 0;
    unsigned previous_day = 1;
    for (Index index = 0; index < cases.size(); ++index) {
        const Case& item = cases[index];
        if (item.day != previous_day) {
            std::cerr << "Scored snapshot " << previous_day << ", " << index << " cumulative cases\n";
            previous_day = item.day;
        }
        if (item.day < 1 || item.day == 255 || item.kind > cycle_4 ||
                (item.kind >= cycle_2 && item.degree != item.kind))
            throw std::runtime_error("Invalid case record");
        const Time cutoff = item.day * day_minutes, from = cutoff - 7 * day_minutes;
        Result result;
        result.offset = offset;
        evidence.clear();
        if (item.kind < cycle_2) fan(view, item, from, cutoff, index + 1, scratch, evidence, result);
        else cycle(view, item, from, cutoff, evidence, result);
        result.keep = keep_mask(item.kind, result.signals);
        result.tier = rank(item.kind, result.signals, result.keep);
        const unsigned case_period = period(item.day);
        ordinals.clear();
        for (Index payment : evidence) {
            const Fact& fact = facts[payment];
            ordinals.push_back(fact.ordinal);
            if (period(fact.minute / day_minutes + 1) != case_period) continue;
            flags[fact.ordinal] |= result.keep;
            motifs[fact.ordinal] |= 1 << item.kind;
            if (item.kind == fan_out)
                max_fan_out_degree[fact.ordinal] = std::max(max_fan_out_degree[fact.ordinal], item.degree);
        }
        write(payments, std::span<const Index>(ordinals));
        write(scored, std::span<const Result>(&result, 1));
        offset += evidence.size();
    }
    if (offset != expected_memberships)
        throw std::runtime_error("The reconstructed evidence population differs from AWS");
    std::ofstream f(root / "flags.u16", std::ios::binary), m(root / "motifs.u8", std::ios::binary),
                  d(root / "max-degree.u32", std::ios::binary);
    write(f, std::span<const std::uint16_t>(flags));
    write(m, std::span<const std::uint8_t>(motifs));
    write(d, std::span<const Index>(max_fan_out_degree));
    std::cerr << "Replayed all " << offset << " published case/evidence memberships\n";
}

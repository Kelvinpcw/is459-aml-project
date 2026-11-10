#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <numbers>
#include <numeric>
#include <span>
#include <stdexcept>
#include <thread>
#include <vector>

using Id = std::uint32_t;
using Minute = std::int32_t;
using Money = __uint128_t;
using Rows = std::span<const Id>;
constexpr Minute day = 1440;

struct Amount {
    std::uint64_t low, high;
    double units() const { return double((Money(high) << 64) | low) / 100'000'000; }
};

struct Fact {
    Amount paid, received;
    Id ordinal, sender, receiver;
    Minute minute;
    std::uint16_t paid_currency, received_currency;
    Id pad;
};

struct Case {
    std::uint8_t kind, day;
    std::uint16_t pad;
    Id size, degree;
    std::array<Id, 4> nodes;
};

struct Rule {
    std::uint64_t offset;
    std::uint16_t keep, signals;
    std::uint8_t tier, path_length;
    std::uint16_t pad;
    std::array<Id, 4> path;
    Id context, unused;
};

struct Graph {
    Id peers = 0;
    std::uint8_t motifs = 0, tier = 0;
};

struct Index {
    std::vector<Id> rows, offsets;
    Rows for_node(Id id) const {
        return std::span(rows).subspan(offsets[id], offsets[id+1] - offsets[id]);
    }
};

struct View {
    const std::vector<Fact>& facts;
    const Index& out;
    const Index& in;
    const Index& edges;
};

struct Counts {
    Id previous_24h, previous_7d, today, current_minute;
};

constexpr std::array names{
    "log_paid", "log_received", "payment_currency", "receiving_currency", "payment_format",
    "self_transfer", "same_bank", "same_currency", "hour_sine", "hour_cosine",
    "sender_out_prior_24h", "sender_in_prior_24h", "receiver_in_prior_24h", "receiver_out_prior_24h",
    "sender_out_prior_7d", "sender_in_prior_7d", "receiver_in_prior_7d", "receiver_out_prior_7d",
    "sender_out_today", "sender_in_today", "receiver_in_today", "receiver_out_today",
    "sender_distinct_recipients_today", "receiver_distinct_senders_today",
    "same_pair_prior_7d", "reverse_pair_prior_7d", "same_pair_today", "reverse_pair_today",
    "gap_from_sender_receipt", "sender_receipt_amount_similarity", "gap_to_receiver_outflow_today",
    "receiver_outflow_amount_similarity", "sender_out_same_minute", "receiver_in_same_minute",
    "fan_in", "fan_out", "cycle_2", "cycle_3", "cycle_4", "max_fan_counterparties", "rule_priority",
};
using Features = std::array<float, names.size()>;
static_assert(sizeof(Fact) == 56 && sizeof(Case) == 28 && sizeof(Rule) == 40 && sizeof(Features) == 4 * names.size());

template <class T>
std::vector<T> load(const std::filesystem::path& file, std::size_t n) {
    if (std::filesystem::file_size(file) != n * sizeof(T))
        throw std::runtime_error("Wrong input count for " + file.string());
    std::vector<T> result(n);
    std::ifstream stream(file, std::ios::binary);
    if (!stream.read(reinterpret_cast<char*>(result.data()), n * sizeof(T)))
        throw std::runtime_error("Read failed for " + file.string());
    return result;
}

template <class T>
void write(std::ofstream& stream, const std::vector<T>& rows) {
    if (!stream.write(reinterpret_cast<const char*>(rows.data()), rows.size() * sizeof(T)))
        throw std::runtime_error("Writing model inputs failed");
}

template <class Key, class Sort>
Index index_by(const std::vector<Fact>& facts, Id accounts, Key key, Sort order) {
    std::vector<Id> offsets(accounts + 1);
    for (const auto& f : facts) {
        if (f.sender >= accounts || f.receiver >= accounts)
            throw std::runtime_error("Account is outside the verified codebook");
        if (f.sender != f.receiver) ++offsets[key(f) + 1];
    }
    std::partial_sum(offsets.begin(), offsets.end(), offsets.begin());
    auto cursor = offsets;
    std::vector<Id> rows(offsets.back());
    for (Id i = 0; i < facts.size(); ++i)
        if (facts[i].sender != facts[i].receiver) rows[cursor[key(facts[i])]++] = i;
    for (Id i = 0; i < accounts; ++i)
        std::sort(rows.begin()+offsets[i], rows.begin()+offsets[i+1], order);
    return {std::move(rows), std::move(offsets)};
}

Rows edge(const View& view, Id sender, Id receiver) {
    const Rows rows = view.edges.for_node(sender);
    auto first = std::lower_bound(rows.begin(), rows.end(), receiver,
                                   [&](Id row, Id to) { return view.facts[row].receiver < to; });
    auto end = std::upper_bound(first, rows.end(), receiver,
                                 [&](Id to, Id row) { return to < view.facts[row].receiver; });
    return {first, end};
}

Rows::iterator at_least(Rows span, const View& view, Minute threshold) {
    return std::lower_bound(span.begin(), span.end(), threshold,
                            [&](Id row, Minute t) { return view.facts[row].minute < t; });
}

Counts activity(Rows rows, const View& view, Minute t, Minute first, Minute end) {
    auto now = at_least(rows, view, t);
    auto prior = at_least(rows, view, t - 7 * day);
    auto yesterday = at_least(rows, view, t - day);
    auto start = at_least(rows, view, first);
    auto close = at_least(rows, view, end);
    auto minute_after = at_least(rows, view, t + 1);
    return {Id(now - yesterday), Id(now - prior), Id(close - start), Id(minute_after - now)};
}

std::vector<Id> distinct_daily(const std::vector<Fact>& facts, const Index& index, Id accounts, Id Fact::*peer) {
    std::vector<Id> degree(facts.size()), stamped(accounts);
    Id stamp = 0;
    for (Id node = 0; node < accounts; ++node) {
        const auto rows = index.for_node(node);
        for (std::size_t i = 0, end = 0; i < rows.size(); i = end) {
            const Minute date = facts[rows[i]].minute / day;
            Id unique = 0;
            ++stamp;
            while (end < rows.size() && facts[rows[end]].minute / day == date) {
                const Id other = facts[rows[end++]].*peer;
                unique += stamped[other] != stamp;
                stamped[other] = stamp;
            }
            for (std::size_t k = i; k < end; ++k) degree[rows[k]] = unique;
        }
    }
    return degree;
}

std::vector<Graph> day_end_graph(const std::filesystem::path& replay, const std::vector<std::uint8_t>& dates,
                               Id payments, Id cases, std::size_t memberships) {
    const auto descriptors = load<Case>(replay / "cases.bin", cases);
    const auto decisions = load<Rule>(replay / "scored.bin", cases);
    const auto evidence = load<Id>(replay / "evidence.u32", memberships);
    std::vector<Graph> graph(payments + 1);
    std::size_t offset = 0;
    for (Id i = 0; i < cases; ++i) {
        const auto& c = descriptors[i];
        const auto& r = decisions[i];
        if (r.offset != offset || offset + c.size > memberships || c.day < 1 || c.day == 255 || c.kind > 4)
            throw std::runtime_error("Published case and evidence are out of alignment");
        for (Id id : std::span(evidence).subspan(offset, c.size)) {
            if (id == 0 || id > payments || dates[id] > c.day)
                throw std::runtime_error("Case evidence crosses its as-of time");
            if (dates[id] != c.day) continue;
            auto& features = graph[id];
            features.motifs |= 1 << c.kind;
            features.tier = std::max(features.tier, r.tier);
            if (c.kind < 2) features.peers = std::max(features.peers, c.degree);
        }
        offset += c.size;
    }
    if (offset != memberships) throw std::runtime_error("Incomplete daily case evidence");
    return graph;
}

float logged(Id n) { return std::log1p(float(n)); }

float amount_ratio(const Amount& a, const Amount& b) {
    const double x = a.units(), y = b.units();
    if (x <= 0 || y <= 0) return 0;
    return std::min(x,y) / std::max(x,y);
}

struct Inputs {
    const std::vector<std::uint8_t>& formats;
    const std::vector<Id>& banks;
    const std::vector<Id>& send_degree;
    const std::vector<Id>& receive_degree;
    const std::vector<Graph>& graph;
    std::array<float, day> sine, cosine;
};

Features features(const View& view, const Inputs& input, Id row) {
    const auto& f = view.facts[row];
    const Minute minute = f.minute, first = (minute / day) * day, end = first + day;
    const auto si = view.in.for_node(f.sender), so = view.out.for_node(f.sender);
    const auto ri = view.in.for_node(f.receiver), ro = view.out.for_node(f.receiver);
    const auto sender_out = activity(so, view, minute, first, end);
    const auto sender_in = activity(si, view, minute, first, end);
    const auto receiver_in = activity(ri, view, minute, first, end);
    const auto receiver_out = activity(ro, view, minute, first, end);
    const auto direct = activity(edge(view, f.sender, f.receiver), view, minute, first, end);
    const auto reverse = activity(edge(view, f.receiver, f.sender), view, minute, first, end);

    float prior_gap = -1, prior_value = -1, later_gap = -1, later_value = -1;
    auto previous = at_least(si, view, minute);
    if (previous != si.begin()) {
        const auto& receipt = view.facts[*std::prev(previous)];
        if (minute - receipt.minute <= day) {
            prior_gap = logged(minute - receipt.minute);
            if (receipt.received_currency == f.paid_currency) prior_value = amount_ratio(receipt.received, f.paid);
        }
    }
    auto next = at_least(ro, view, minute + 1);
    if (next != ro.end()) {
        const auto& onward = view.facts[*next];
        if (onward.minute < end) {
            later_gap = logged(onward.minute - minute);
            if (onward.paid_currency == f.received_currency) later_value = amount_ratio(f.received, onward.paid);
        }
    }
    const auto g = input.graph[f.ordinal];
    return {
        float(std::log1p(f.paid.units())), float(std::log1p(f.received.units())), float(f.paid_currency),
        float(f.received_currency), float(input.formats[f.ordinal]), float(f.sender == f.receiver),
        float(input.banks[f.sender] == input.banks[f.receiver]), float(f.paid_currency == f.received_currency),
        input.sine[minute-first], input.cosine[minute-first],
        logged(sender_out.previous_24h), logged(sender_in.previous_24h), logged(receiver_in.previous_24h),
        logged(receiver_out.previous_24h), logged(sender_out.previous_7d), logged(sender_in.previous_7d),
        logged(receiver_in.previous_7d), logged(receiver_out.previous_7d), logged(sender_out.today),
        logged(sender_in.today), logged(receiver_in.today), logged(receiver_out.today),
        logged(input.send_degree[row]), logged(input.receive_degree[row]), logged(direct.previous_7d),
        logged(reverse.previous_7d), logged(direct.today), logged(reverse.today), prior_gap, prior_value,
        later_gap, later_value, logged(sender_out.current_minute), logged(receiver_in.current_minute),
        float((g.motifs & 1) != 0), float((g.motifs & 2) != 0), float((g.motifs & 4) != 0),
        float((g.motifs & 8) != 0), float((g.motifs & 16) != 0), logged(g.peers), float(g.tier),
    };
}

int main(int argc, char** argv) {
    if (argc != 4 && argc != 7)
        throw std::invalid_argument("Usage: features replay-directory work-directory account-count [payments cases memberships]");
    const std::filesystem::path replay = argv[1], work = argv[2];
    const auto accounts = Id(std::stoul(argv[3]));
    const Id payments = argc == 7 ? std::stoul(argv[4]) : 31'898'238;
    const Id cases = argc == 7 ? std::stoul(argv[5]) : 2'251'155;
    const std::size_t memberships = argc == 7 ? std::stoull(argv[6]) : 81'321'105;
    if (!accounts) throw std::invalid_argument("Expected nonempty account codebook");
    const auto facts = load<Fact>(replay / "facts.bin", payments);
    const auto dates = load<std::uint8_t>(replay / "days.u8", payments + 1);
    const auto formats = load<std::uint8_t>(work / "formats.u8", payments + 1);
    const auto banks = load<Id>(work / "banks.u32", accounts);
    const auto graph = day_end_graph(replay, dates, payments, cases, memberships);
    std::cerr << "Verified label-free daily graph inputs for all published cases\n";

    auto sender = [](const Fact& f) { return f.sender; };
    auto receiver = [](const Fact& f) { return f.receiver; };
    auto chronological = [&](Id a, Id b) {
        return facts[a].minute != facts[b].minute ? facts[a].minute < facts[b].minute :
                                                   facts[a].ordinal < facts[b].ordinal;
    };
    auto pair_order = [&](Id a, Id b) {
        return facts[a].receiver != facts[b].receiver ? facts[a].receiver < facts[b].receiver : chronological(a,b);
    };
    const auto out = index_by(facts, accounts, sender, chronological);
    const auto in = index_by(facts, accounts, receiver, chronological);
    const auto pairs = index_by(facts, accounts, sender, pair_order);
    const auto sent = distinct_daily(facts, out, accounts, &Fact::receiver);
    const auto received = distinct_daily(facts, in, accounts, &Fact::sender);
    const View view{facts, out, in, pairs};
    Inputs input{formats, banks, sent, received, graph, {}, {}};
    for (Minute t = 0; t < day; ++t) {
        input.sine[t] = std::sin(2 * std::numbers::pi * t / day);
        input.cosine[t] = std::cos(2 * std::numbers::pi * t / day);
    }
    std::ofstream matrix(work / "features.f32", std::ios::binary), ids(work / "ordinals.u32", std::ios::binary);
    std::ofstream fields(work / "feature-names.txt");
    for (const char* name : names) fields << name << '\n';
    constexpr Id chunk = 196'608, workers = 6;
    for (Id from = 0; from < payments; from += chunk) {
        const Id n = std::min(chunk, payments-from);
        std::vector<Features> data(n);
        std::vector<Id> ordinal(n);
        {
            std::vector<std::thread> threads;
            for (Id worker = 0; worker < workers; ++worker) {
                const Id start = worker * n / workers, end = (worker+1)*n/workers;
                threads.emplace_back([&, start, end] {
                    for (Id i = start; i < end; ++i) {
                        const Id row = from + i;
                        data[i] = features(view, input, row);
                        ordinal[i] = facts[row].ordinal;
                    }
                });
            }
            for (auto& thread : threads) thread.join();
        }
        write(matrix, data);
        write(ids, ordinal);
        if ((from / chunk) % 10 == 0 || from + n == payments)
            std::cerr << "Computed " << from+n << " / " << payments << " payment feature rows\n";
    }
}

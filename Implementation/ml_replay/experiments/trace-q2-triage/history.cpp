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
    const Index& first_out;
    const Index& first_in;
};

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

std::pair<Index, Index> first_partners(const std::vector<Fact>& facts,
                                       const Index& pairs, Id accounts) {
    std::vector<std::uint8_t> first(facts.size());
    for (Id account = 0; account < accounts; ++account) {
        Id prior = accounts;
        for (Id row: pairs.for_node(account)) {
            const Id receiver = facts[row].receiver;
            if (receiver != prior) first[row] = 1;
            prior = receiver;
        }
    }
    const auto build = [&](bool outgoing) {
        const auto key = [&](Id row) {
            return outgoing ? facts[row].sender : facts[row].receiver;
        };
        std::vector<Id> offsets(accounts + 1);
        for (Id row = 0; row < facts.size(); ++row)
            if (first[row]) ++offsets[key(row) + 1];
        std::partial_sum(offsets.begin(), offsets.end(), offsets.begin());
        std::vector<Id> rows(offsets.back());
        auto cursor = offsets;
        for (Id row = 0; row < facts.size(); ++row)
            if (first[row]) rows[cursor[key(row)]++] = row;
        for (Id i = 0; i < accounts; ++i)
            std::sort(rows.begin() + offsets[i], rows.begin() + offsets[i+1],
                      [&](Id a, Id b) { return facts[a].minute < facts[b].minute; });
        return Index{std::move(rows), std::move(offsets)};
    };
    return {build(true), build(false)};
}

Rows::iterator at_least(Rows span, const View& view, Minute threshold) {
    return std::lower_bound(span.begin(), span.end(), threshold,
                            [&](Id row, Minute t) { return view.facts[row].minute < t; });
}

struct Counts {
    Id last_hour, last_day, last_week;
};

constexpr std::array names{
    "log_amount_paid", "log_amount_received", "payment_currency", "receiving_currency",
    "payment_format", "self_transfer", "same_bank", "same_currency", "hour_sine", "hour_cosine",
    "sender_out_1h", "sender_in_1h", "receiver_in_1h", "receiver_out_1h",
    "sender_out_24h", "sender_in_24h", "receiver_in_24h", "receiver_out_24h",
    "sender_out_7d", "sender_in_7d", "receiver_in_7d", "receiver_out_7d",
    "forward_pair_7d", "reverse_pair_7d", "gap_from_prior_sender_receipt",
    "prior_sender_receipt_same_currency_similarity", "gap_from_prior_receiver_outflow",
    "prior_receiver_outflow_same_currency_similarity",
    "forward_pair_prior_count", "forward_pair_age", "forward_pair_last_gap",
    "sender_prior_distinct_recipients", "receiver_prior_distinct_senders",
    "sender_new_recipients_1h", "sender_new_recipients_24h", "sender_new_recipients_7d",
    "receiver_new_senders_1h", "receiver_new_senders_24h", "receiver_new_senders_7d",
    "sender_new_recipient_share_24h", "receiver_new_sender_share_24h",
    "sender_outgoing_age", "receiver_incoming_age",
};
using Features = std::array<float, names.size()>;

struct Meta {
    Id ordinal;
    Minute minute;
};

static_assert(sizeof(Fact)==56 && sizeof(Meta)==8 && sizeof(Features)==4*names.size());

Counts past(Rows rows, const View& view, Minute minute) {
    auto end = at_least(rows, view, minute);
    const Rows observed(rows.begin(), end);
    return {Id(end - at_least(observed, view, minute-60)),
            Id(end - at_least(observed, view, minute-day)),
            Id(end - at_least(observed, view, minute-7*day))};
}

float logged(Id n) { return std::log1p(float(n)); }

float amount_ratio(const Amount& a, const Amount& b) {
    const double x = a.units(), y = b.units();
    if (x <= 0 || y <= 0) return 0;
    return std::min(x,y)/std::max(x,y);
}

struct Inputs {
    const std::vector<std::uint8_t>& formats;
    const std::vector<Id>& banks;
    std::array<float, day> sine, cosine;
};

Features derive(const View& view, const Inputs& input, Id row) {
    const Fact& f = view.facts[row];
    const Minute t = f.minute;
    const auto si = view.in.for_node(f.sender), so = view.out.for_node(f.sender);
    const auto ri = view.in.for_node(f.receiver), ro = view.out.for_node(f.receiver);
    const auto sent = past(so, view, t), funded = past(si, view, t);
    const auto received = past(ri, view, t), onward = past(ro, view, t);
    const auto pair = edge(view, f.sender, f.receiver);
    const auto forward = past(pair, view, t);
    const auto first_out = view.first_out.for_node(f.sender);
    const auto first_in = view.first_in.for_node(f.receiver);
    const auto new_out = past(first_out, view, t), new_in = past(first_in, view, t);
    const auto pair_end = at_least(pair, view, t);
    const auto age = [&](Rows rows) {
        return rows.empty() || view.facts[rows.front()].minute >= t
            ? -1.0f : logged(t - view.facts[rows.front()].minute);
    };
    const auto reverse = past(edge(view, f.receiver, f.sender), view, t);
    float in_gap = -1, in_value = -1, out_gap = -1, out_value = -1;
    auto previous = at_least(si, view, t);
    if (previous != si.begin()) {
        const Fact& older = view.facts[*std::prev(previous)];
        if (t - older.minute <= day) {
            in_gap = logged(t - older.minute);
            if (older.received_currency == f.paid_currency)
                in_value = amount_ratio(older.received, f.paid);
        }
    }
    previous = at_least(ro, view, t);
    if (previous != ro.begin()) {
        const Fact& older = view.facts[*std::prev(previous)];
        if (t - older.minute <= day) {
            out_gap = logged(t - older.minute);
            if (f.received_currency == older.paid_currency)
                out_value = amount_ratio(f.received, older.paid);
        }
    }
    return {
        float(std::log1p(f.paid.units())), float(std::log1p(f.received.units())),
        float(f.paid_currency), float(f.received_currency), float(input.formats[f.ordinal]),
        float(f.sender == f.receiver), float(input.banks[f.sender] == input.banks[f.receiver]),
        float(f.paid_currency == f.received_currency), input.sine[t%day], input.cosine[t%day],
        logged(sent.last_hour), logged(funded.last_hour), logged(received.last_hour), logged(onward.last_hour),
        logged(sent.last_day), logged(funded.last_day), logged(received.last_day), logged(onward.last_day),
        logged(sent.last_week), logged(funded.last_week), logged(received.last_week), logged(onward.last_week),
        logged(forward.last_week), logged(reverse.last_week), in_gap, in_value, out_gap, out_value,
        logged(Id(pair_end-pair.begin())), age(pair),
        pair_end == pair.begin() ? -1.0f : logged(t - view.facts[*std::prev(pair_end)].minute),
        logged(Id(at_least(first_out, view, t) - first_out.begin())),
        logged(Id(at_least(first_in, view, t) - first_in.begin())),
        logged(new_out.last_hour), logged(new_out.last_day), logged(new_out.last_week),
        logged(new_in.last_hour), logged(new_in.last_day), logged(new_in.last_week),
        sent.last_day ? float(new_out.last_day) / sent.last_day : 0.0f,
        received.last_day ? float(new_in.last_day) / received.last_day : 0.0f,
        age(so), age(ri),
    };
}

int main(int argc, char** argv) {
    if (argc != 5 && argc != 6)
        throw std::invalid_argument("Usage: features replay-input formats-input working-folder accounts [payments]");
    const std::filesystem::path replay = argv[1], auxiliary = argv[2], work = argv[3];
    const auto accounts = Id(std::stoul(argv[4]));
    const Id payments = argc == 6 ? std::stoul(argv[5]) : 31'898'238;
    const auto facts = load<Fact>(replay/"facts.bin", payments);
    const auto formats = load<std::uint8_t>(auxiliary/"formats.u8", payments+1);
    const auto banks = load<Id>(auxiliary/"banks.u32", accounts);
    auto sender = [](const Fact& f){ return f.sender; };
    auto receiver = [](const Fact& f){ return f.receiver; };
    auto chronological = [&](Id a, Id b){
        return facts[a].minute != facts[b].minute ? facts[a].minute < facts[b].minute :
                                                   facts[a].ordinal < facts[b].ordinal;
    };
    auto pairs = [&](Id a, Id b){
        return facts[a].receiver != facts[b].receiver ? facts[a].receiver < facts[b].receiver :
                                                       chronological(a,b);
    };
    const auto out = index_by(facts, accounts, sender, chronological);
    const auto in = index_by(facts, accounts, receiver, chronological);
    const auto edges = index_by(facts, accounts, sender, pairs);
    const auto [new_out, new_in] = first_partners(facts, edges, accounts);
    const View view{facts, out, in, edges, new_out, new_in};
    Inputs input{formats, banks, {}, {}};
    for (Minute t=0; t<day; ++t) {
        input.sine[t] = std::sin(2 * std::numbers::pi * t / day);
        input.cosine[t] = std::cos(2 * std::numbers::pi * t / day);
    }
    std::ofstream matrix(work/"features.f32", std::ios::binary), metadata(work/"payments.bin", std::ios::binary);
    std::ofstream fields(work/"feature-names.txt");
    for (auto name: names) fields << name << '\n';
    fields.close();
    constexpr Id batch=196608, workers=6;
    for (Id from=0; from<payments; from+=batch) {
        const Id count = std::min(batch,payments-from);
        std::vector<Features> output(count);
        std::vector<Meta> meta(count);
        std::vector<std::thread> threads;
        for (Id w=0; w<workers; ++w) {
            const Id first=w*count/workers, last=(w+1)*count/workers;
            threads.emplace_back([&,first,last]{
                for (Id i=first; i<last; ++i) {
                    const Id row=from+i;
                    output[i]=derive(view,input,row);
                    meta[i]={facts[row].ordinal,facts[row].minute};
                }
            });
        }
        for (auto& thread:threads) thread.join();
        write(matrix,output);
        write(metadata,meta);
        if ((from/batch)%16==0 || from+count==payments)
            std::cerr << "Computed strictly prior features for " << from+count << " payments\n";
    }
}

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <numeric>
#include <span>
#include <stdexcept>
#include <thread>
#include <vector>

using Id = std::uint32_t;
using Minute = std::int32_t;
using Rows = std::span<const Id>;
constexpr Minute day = 1440;

struct Amount {
    std::uint64_t low, high;
    double units() const { return double(((__uint128_t(high) << 64) | low)) / 100'000'000; }
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
    Rows for_node(Id node) const {
        return Rows(rows).subspan(offsets[node], offsets[node+1] - offsets[node]);
    }
};

struct View {
    const std::vector<Fact>& facts;
    const Index& outgoing;
    const Index& incoming;
    const Index& pairs;
    const Index& new_payees;
    const std::vector<std::uint8_t>& formats;
    const std::vector<Id>& banks;
};

template<class T>
std::vector<T> load(const std::filesystem::path& file, std::size_t count) {
    if (std::filesystem::file_size(file) != count * sizeof(T))
        throw std::runtime_error("Unexpected input size for " + file.string());
    std::ifstream stream(file, std::ios::binary);
    std::vector<T> values(count);
    if (!stream.read(reinterpret_cast<char*>(values.data()), values.size() * sizeof(T)))
        throw std::runtime_error("Reading " + file.string() + " failed");
    return values;
}

template<class Node, class Order>
Index index_rows(Rows rows, Id accounts, Node node, Order order) {
    std::vector<Id> offsets(accounts+1);
    for (Id row: rows) ++offsets.at(node(row)+1);
    std::partial_sum(offsets.begin(), offsets.end(), offsets.begin());
    auto cursor = offsets;
    std::vector<Id> ordered(rows.size());
    for (Id row: rows) ordered[cursor[node(row)]++] = row;
    for (Id a=0; a<accounts; ++a)
        std::sort(ordered.begin()+offsets[a], ordered.begin()+offsets[a+1], order);
    return {std::move(ordered), std::move(offsets)};
}

Rows pair_rows(const View& view, const Fact& fact) {
    auto rows = view.pairs.for_node(fact.sender);
    auto first = std::lower_bound(rows.begin(), rows.end(), fact.receiver,
        [&](Id row, Id receiver) { return view.facts[row].receiver < receiver; });
    auto last = std::upper_bound(first, rows.end(), fact.receiver,
        [&](Id receiver, Id row) { return receiver < view.facts[row].receiver; });
    return {first, last};
}

Rows::iterator at_least(Rows rows, const View& view, Minute time) {
    return std::lower_bound(rows.begin(), rows.end(), time,
        [&](Id row, Minute minute) { return view.facts[row].minute < minute; });
}

Rows earlier(Rows rows, const View& view, Minute time) {
    return {rows.begin(), at_least(rows, view, time)};
}

float count_since(Rows rows, const View& view, Minute time) {
    return float(rows.end() - at_least(rows, view, time));
}

float age_days(Rows rows, const View& view, Minute time) {
    return rows.empty() ? 0 : float(time-view.facts[rows.front()].minute)/day;
}

float gap_hours(Rows rows, const View& view, Minute time) {
    return rows.empty() ? std::numeric_limits<float>::quiet_NaN()
                        : float(time-view.facts[rows.back()].minute)/60;
}

constexpr std::array names{
    "hour", "day_of_week", "log_amount_paid", "receiving_currency", "payment_currency",
    "payment_format", "cross_currency", "cross_bank", "self_transfer",
    "is_first_pair", "pair_prev_count", "pair_age_days", "hours_since_last_pair",
    "sender_prev_count", "sender_age_days", "hours_since_last_sender_tx", "sender_prev_partners",
    "receiver_prev_count", "receiver_age_days", "new_payee_share_24h",
    "sender_tx_1h", "sender_new_payees_1h", "receiver_tx_1h",
    "sender_tx_24h", "sender_new_payees_24h", "receiver_tx_24h",
    "sender_tx_7d", "sender_new_payees_7d", "receiver_tx_7d",
};

using Features = std::array<float, names.size()>;
static_assert(sizeof(Fact)==56 && sizeof(Features)==4*names.size());

Features features(const View& view, Id row) {
    const Fact& tx = view.facts[row];
    const Minute t = tx.minute;
    const auto pair = earlier(pair_rows(view, tx), view, t);
    const auto out = earlier(view.outgoing.for_node(tx.sender), view, t);
    const auto in = earlier(view.incoming.for_node(tx.receiver), view, t);
    const auto payees = earlier(view.new_payees.for_node(tx.sender), view, t);
    const float sent_24h = count_since(out, view, t-day);
    const float new_24h = count_since(payees, view, t-day);
    return {
        float((t%day)/60), float((t/day+3)%7), float(std::log1p(tx.paid.units())),
        float(tx.received_currency), float(tx.paid_currency), float(view.formats[tx.ordinal]),
        float(tx.paid_currency != tx.received_currency),
        float(view.banks[tx.sender] != view.banks[tx.receiver]), float(tx.sender == tx.receiver),
        float(pair.empty()), float(pair.size()), age_days(pair,view,t), gap_hours(pair,view,t),
        float(out.size()), age_days(out,view,t), gap_hours(out,view,t), float(payees.size()),
        float(in.size()), age_days(in,view,t), sent_24h == 0 ? 0 : new_24h/sent_24h,
        count_since(out,view,t-60), count_since(payees,view,t-60), count_since(in,view,t-60),
        sent_24h, new_24h, count_since(in,view,t-day),
        count_since(out,view,t-7*day), count_since(payees,view,t-7*day), count_since(in,view,t-7*day),
    };
}

int main(int argc, char** argv) {
    if (argc != 6) throw std::invalid_argument("Usage: features facts-folder aux-folder output-folder payments accounts");
    const std::filesystem::path fact_folder=argv[1], auxiliary=argv[2], output=argv[3];
    const Id count=std::stoul(argv[4]), accounts=std::stoul(argv[5]);
    const auto facts=load<Fact>(fact_folder/"facts.bin", count);
    const auto formats=load<std::uint8_t>(auxiliary/"formats.u8", count+1);
    const auto banks=load<Id>(auxiliary/"banks.u32", accounts);
    const auto sender=[&](Id row) { return facts[row].sender; };
    const auto receiver=[&](Id row) { return facts[row].receiver; };
    const auto chron=[&](Id a, Id b) {
        return facts[a].minute != facts[b].minute ? facts[a].minute < facts[b].minute
                                                   : facts[a].ordinal < facts[b].ordinal;
    };
    std::vector<Id> rows(count);
    std::iota(rows.begin(),rows.end(),0);
    const auto outgoing=index_rows(rows,accounts,sender,chron);
    const auto incoming=index_rows(rows,accounts,receiver,chron);
    const auto pairs=index_rows(rows,accounts,sender,[&](Id a, Id b) {
        return receiver(a)!=receiver(b) ? receiver(a)<receiver(b) : chron(a,b);
    });
    rows.clear();
    rows.shrink_to_fit();
    std::vector<Id> first_pairs;
    for (Id a=0; a<accounts; ++a) {
        Id previous=accounts;
        for (Id row: pairs.for_node(a)) {
            if (receiver(row)!=previous) first_pairs.push_back(row);
            previous=receiver(row);
        }
    }
    const auto new_payees=index_rows(first_pairs,accounts,sender,chron);
    first_pairs.clear();
    first_pairs.shrink_to_fit();
    const View view{facts,outgoing,incoming,pairs,new_payees,formats,banks};
    std::ofstream matrix(output/"features.f32", std::ios::binary);
    std::ofstream fields(output/"feature-names.txt");
    for (const auto name: names) fields << name << '\n';
    if (!fields) throw std::runtime_error("Writing feature contract failed");
    constexpr Id batch=262144, workers=4;
    for (Id offset=0; offset<count; offset+=batch) {
        const Id length=std::min(batch,count-offset);
        std::vector<Features> block(length);
        std::vector<std::thread> pool;
        for (Id worker=0; worker<workers; ++worker)
            pool.emplace_back([&,worker] {
                for (Id i=worker*length/workers; i<(worker+1)*length/workers; ++i)
                    block[i]=features(view,offset+i);
            });
        for (auto& thread: pool) thread.join();
        if (!matrix.write(reinterpret_cast<const char*>(block.data()), block.size()*sizeof(Features)))
            throw std::runtime_error("Writing feature matrix failed");
        if (offset==0 || offset+length==count || (offset/batch)%16==15)
            std::cerr << "Computed as-of features for " << offset+length << " of " << count << " payments\n";
    }
}

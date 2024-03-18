#include <iostream>
#include <string>
#include <fstream>
#include "rl_agent.h"

using namespace std;
using namespace nlohmann;

const char * RequestBandwidthCommand = "RequestBandwidth";

void rl_agent::ReportStates(
    std::uint64_t sendTimeMs,
    std::uint64_t receiveTimeMs,
    std::size_t payloadSize,
    std::uint8_t payloadType,
    std::uint16_t sequenceNumber,
    std::uint32_t ssrc,
    std::size_t paddingLength,
    std::size_t headerLength) {

    nlohmann::json j;
    j["send_time_ms"] = sendTimeMs;
    j["arrival_time_ms"] = receiveTimeMs;
    j["payload_type"] = payloadType;
    j["sequence_number"] = sequenceNumber;
    j["ssrc"] = ssrc;
    j["padding_length"] = paddingLength;
    j["header_length"] = headerLength;
    j["payload_size"] = payloadSize;

    std::cout << j.dump() << std::endl;
}

float rl_agent::GetEstimatedBandwidth() {
    std::string bandwidth;
    std::cout << RequestBandwidthCommand << std::endl;
    std::cin >> bandwidth;
    std::cout << "BANDWIDTH Received " << bandwidth << std::endl;
    return std::stof(bandwidth);
}

from r2a.ir2a import IR2A
from player.parser import *

import statistics
import time
import math


class R2A_BBA2(IR2A):
    def __init__(self, id):
        IR2A.__init__(self, id)

        self.qi = []
        self.throughputs = []

        self.quality_step_constant = 2

        self.capacity_duration = None
        self.last_request_time = None

        self.max_reservoir = 140
        self.min_reservoir: int = 8

        self.reservoir = 90
        self.upper_reservoir = 216

        self.rate_index: int = 0
        self.rate_index_min: int = 0
        self.rate_index_max: int = None

        self.buffer_size: int = 0

    def handle_xml_request(self, msg):
        self.request_time = time.perf_counter()
        self.send_down(msg)

    def handle_xml_response(self, msg):
        self.parsed_mpd = parse_mpd(msg.get_payload())

        self.qi = self.parsed_mpd.get_qi()
        self.rate_index_max = len(self.qi) - 1

        self.last_request_time = time.time()

        self.send_up(msg)

    def handle_segment_size_request(self, msg):
        self.buffer_size = self.whiteboard.get_amount_video_to_play()

        new_rate_index_startup = None
        buffer_decreasing = False
        if (
            self.capacity_duration is not None
            and self.rate_index + 1 < self.rate_index_max
        ):
            chunk_size = self.qi[self.rate_index]
            capacity = chunk_size / self.capacity_duration

            buffer_decreasing = self.capacity_duration >= 1

            # Calculate ideal based on capacity in startup phase
            ideal_rate_quality = capacity / self.quality_step_constant

            if ideal_rate_quality >= self.qi[self.rate_index + 1]:
                new_rate_index_startup = self.rate_index + 1

        if self.buffer_size <= self.reservoir:
            new_rate_index_buffer = self.rate_index_min
        elif self.buffer_size >= self.upper_reservoir:
            new_rate_index_buffer = self.rate_index_max
        else:
            ideal_rate_index = (
                (self.buffer_size - self.reservoir) * self.rate_index_max
            ) / (self.upper_reservoir - self.reservoir)

            if ideal_rate_index >= (self.rate_index + 1):
                new_rate_index_buffer = math.floor(ideal_rate_index)
            elif ideal_rate_index <= (self.rate_index - 1):
                new_rate_index_buffer = math.ceil(ideal_rate_index)
            else:
                new_rate_index_buffer = self.rate_index

        if new_rate_index_startup is None:
            self.rate_index = new_rate_index_buffer
        elif new_rate_index_buffer > new_rate_index_startup:
            self.rate_index = new_rate_index_buffer
        elif buffer_decreasing:
            self.rate_index = new_rate_index_buffer
        else:
            self.rate_index = new_rate_index_startup

        msg.add_quality_id(self.qi[self.rate_index])

        self.last_request_time = time.perf_counter()

        self.send_down(msg)

    def handle_segment_size_response(self, msg):
        # Estimate network capacity
        time_to_download = time.perf_counter() - self.last_request_time

        # In bits
        average_chunk_size = msg.get_quality_id()
        current_chunk_size = msg.get_bit_length()

        self.throughputs.append(current_chunk_size / time_to_download)

        # The avarage throughput in bits per second
        network_capacity = statistics.mean(self.throughputs)

        # Make reservoir estimation
        target_reservoir = (2 * self.buffer_size) * (
            1 - (average_chunk_size / network_capacity)
        )

        self.reservoir = min(
            max(target_reservoir, self.min_reservoir), self.max_reservoir
        )

        self.send_up(msg)

    def initialize(self):
        pass

    def finalization(self):
        pass

    @staticmethod
    def estimate_immediate_chunck_size():
        pass
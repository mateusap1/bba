from r2a.ir2a import IR2A
from player.parser import *
import time
import math


class R2A_BBA2(IR2A):
    def __init__(self, id):
        IR2A.__init__(self, id)

        self.quality_step_constant = 2

        self.capacity_duration = None
        self.request_time = None

        self.qi = []
        self.throughputs = []

        self.reservoir = 20
        self.upper_reservoir = 54

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

        self.send_up(msg)

    def handle_segment_size_request(self, msg):
        self.buffer_size = self.whiteboard.get_amount_video_to_play()

        new_rate_index = None
        if self.capacity_duration is not None:
            chunk_size = self.qi[self.rate_index]
            capacity = chunk_size / self.capacity_duration

            # Calculate ideal based on capacity in startup phase
            ideal_rate_quality = (capacity / self.quality_step_constant)

            if ideal_rate_quality >= self.qi[self.rate_index + 1]:
                new_rate_index = self.rate_index + 1

        if new_rate_index is not None:
            self.rate_index = new_rate_index
        elif self.buffer_size <= self.reservoir:
            self.rate_index = self.rate_index_min
        elif self.buffer_size >= self.upper_reservoir:
            self.rate_index = self.rate_index_max
        else:
            ideal_rate_index = (
                (self.buffer_size - self.reservoir) * self.rate_index_max
            ) / (self.upper_reservoir - self.reservoir)

            if ideal_rate_index >= (self.rate_index + 1):
                self.rate_index = math.floor(ideal_rate_index)
            elif ideal_rate_index <= (self.rate_index - 1):
                self.rate_index = math.ceil(ideal_rate_index)

        msg.add_quality_id(self.qi[self.rate_index])

        self.request_time = time.perf_counter()

        self.send_down(msg)

    def handle_segment_size_response(self, msg):
        self.capacity_duration = time.perf_counter() - self.request_time

        self.send_up(msg)

    def initialize(self):
        pass

    def finalization(self):
        pass

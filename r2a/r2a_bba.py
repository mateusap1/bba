from r2a.ir2a import IR2A
from player.parser import *
import time
from statistics import mean
import random


# url do video de teste "url_mpd" : "http://164.41.67.41/DASHDatasetTest/BigBuckBunny/1sec/BigBuckBunny_1s_simple_2014_05_09.mpd
# url do video do projeto "url_mpd": "http://45.171.101.167/DASHDataset/BigBuckBunny/1sec/BigBuckBunny_1s_simple_2014_05_09.mpd"
class R2A_BBA(IR2A):

    def __init__(self, id):
        IR2A.__init__(self, id)
        self.qi = []
        self.rate = 0
        self.reservoir = 5
        self.cushion = 10
        self.buffer_size = 0
        self.rate_min = 0
        self.rate_max = 0
        self.max_buf = 60

    def handle_xml_request(self, msg):
        self.send_down(msg)

    def handle_xml_response(self, msg):
        self.parsed_mpd = parse_mpd(msg.get_payload())
        self.qi = self.parsed_mpd.get_qi()

        print(self.parsed_mpd.get_mpd_info())
        print()
        print(self.parsed_mpd.get_segment_template())
        print()
        print(self.parsed_mpd.get_period_info()["duration"])
        print()
        print(self.qi)
        print()
        self.rate_min = 0
        self.rate_max = len(self.qi) - 1

        self.send_up(msg)

    def handle_segment_size_request(self, msg):

        if self.rate == len(self.qi) - 1:
            rate_plus = self.rate_max
        else:
            rate_plus = self.rate + 1
        if self.rate == 0:
            rate_minus = self.rate_min
        else:
            rate_minus = self.rate - 1

        if self.buffer_size <= self.reservoir:
            rate_next = self.rate_min
        elif self.buffer_size >= (self.reservoir + self.cushion):
            rate_next = self.rate_max
        elif self.buffer_size <= self.max_buf * 0.9:
            rate_next = rate_minus
        elif self.buffer_size >= self.max_buf * 0.9:
            rate_next = rate_plus
        else:
            rate_next = self.rate
        self.rate = rate_next
        msg.add_quality_id(self.qi[self.rate])
        self.send_down(msg)

    def handle_segment_size_response(self, msg):
        self.buffer_size = self.whiteboard.get_amount_video_to_play()
        self.send_up(msg)

    def initialize(self):
        pass

    def finalization(self):
        print(self.whiteboard.get_playback_qi())
        print(self.whiteboard.get_playback_buffer_size())

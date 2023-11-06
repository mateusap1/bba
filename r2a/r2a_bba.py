from r2a.ir2a import IR2A
from player.parser import *
import matplotlib.pyplot as plt
from statistics import mean
import time
from base.timer import Timer
import random


# url do video de teste "url_mpd" : "http://164.41.67.41/DASHDatasetTest/BigBuckBunny/1sec/BigBuckBunny_1s_simple_2014_05_09.mpd
# url do video do projeto "url_mpd": "http://45.171.101.167/DASHDataset/BigBuckBunny/1sec/BigBuckBunny_1s_simple_2014_05_09.mpd"
class R2A_BBA(IR2A):

    def __init__(self, id):
        IR2A.__init__(self, id)
        self.qi = []
        self.throughputs = []
        self.timer = Timer.get_instance()
        self.request_time = 0
        self.rate = 0
        self.reservoir = 5
        self.cushion = 10
        self.buffer_size = 0
        self.rate_min = 0
        self.rate_max = 0
        self.max_buf = 60

    def handle_xml_request(self, msg):
        self.request_time = time.perf_counter()
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
        
        self.request_time = time.perf_counter()
        self.send_down(msg)

    def handle_segment_size_response(self, msg):
        self.buffer_size = self.whiteboard.get_amount_video_to_play()

        current_time = self.timer.get_current_time()
        t = time.perf_counter() - self.request_time
        self.throughputs.append((current_time, (msg.get_bit_length() / t)))
 
        self.send_up(msg)

    def initialize(self):
        pass

    def finalization(self):
        self.draw_graphs(self.whiteboard.get_playback_qi(), self.throughputs,
                         "QIvsThroughput", "Quality Index vs. Throughput", "QI")
        self.draw_graphs(self.whiteboard.get_playback_buffer_size(), self.throughputs,
                         "BuffervsThroughput", "Buffer Size vs. Throughput", "Buffer")
        self.draw_graphs(self.whiteboard.get_playback_buffer_size(), 
                         self.whiteboard.get_playback_qi(), "BuffervsQI", 
                         "Buffer Size vs. Quality Index", "Buffer", "QI", tp=False)

    def draw_graphs(self, data1, data2, file_name, title, y_axis_left,
                    y_axis_right="Mbps", x_axis="execution_time (s)", tp=True):
        x1 = [item[0] for item in data1]
        y1 = [item[1] for item in data1]
        
        x2 = [item[0] for item in data2]
        y2 = [item[1] for item in data2]
        
        _, ax1 = plt.subplots()
        ax1.plot(x1, y1, color="blue")
        ax1.set_xlabel(x_axis)
        ax1.set_ylabel(y_axis_left, color="blue")
        ax1.tick_params(axis="y", labelcolor="blue")
        plt.ylim(min(y1), max(y1) * 4 / 3)

        if tp:
            ax2 = ax1.twinx()
            ax2.vlines(x2, [0], y2, color="red")
            ax2.set_ylabel(y_axis_right, color="red")
            ax2.tick_params(axis="y", labelcolor="red")
            plt.ylim(min(y2), max(y2) * 4 / 3)
        else:
            ax2 = ax1.twinx()
            ax2.set_ylabel(y_axis_right, color="green")
            ax2.tick_params(axis="y", labelcolor="green")
            plt.ylim(min(y2), max(y2) * 4 / 3)
            ax1.plot(x2, y2, color="green")

        plt.title(title)
        plt.savefig(f'./results/{file_name}.png')
        plt.clf()
        plt.cla()
        plt.close()
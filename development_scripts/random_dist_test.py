# coding=utf-8
#
# Copyright (c) 2021, Empa, Leonie Fierz
#
# This file is part of CESAR-P - Combined Energy Simulation And Retrofit written in Python
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Contact: https://www.empa.ch/web/s313
#

"""
Little test to check whether drawing random numbers one-by-one or all at once has an influence on their distribution.
"""
import numpy
import pandas

LOW = 0.0
MODE = 3
HIGH = 10.0
NUM_SAMPLES = 100000


def random_draw_one_by_one():
    rand_nums = list()
    for i in range(1, NUM_SAMPLES + 1):
        rand_nums.append(numpy.random.triangular(left=LOW, mode=MODE, right=HIGH))
    return rand_nums


def random_all_at_once():
    return numpy.random.triangular(left=LOW, mode=MODE, right=HIGH, size=NUM_SAMPLES)


if __name__ == "__main__":
    res = pandas.DataFrame.from_dict(data={"one-by-one": random_draw_one_by_one(), "all at once": random_all_at_once()})
    res.to_csv("random_comparison.csv")

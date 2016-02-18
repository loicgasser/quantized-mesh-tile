# -*- coding: utf-8 -*-

import math


def magnitudeSquared(p):
    return p[0] ** 2 + p[1] ** 2 + p[2] ** 2


def magnitude(p):
    return math.sqrt(magnitudeSquared(p))


def add(left, right):
    return [left[0] + right[0], left[1] + right[1], left[2] + right[2]]


def subtract(left, right):
    return [left[0] - right[0], left[1] - right[1], left[2] - right[2]]


def distanceSquared(p1, p2):
    return (p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2 + (p1[2] - p2[2]) ** 2


def distance(p1, p2):
    return math.sqrt(distanceSquared(p1, p2))


def multiplyByScalar(p, scalar):
    return [p[0] * scalar, p[1] * scalar, p[2] * scalar]


def normalize(p):
    mgn = magnitude(p)
    return [p[0] / mgn, p[1] / mgn, p[2] / mgn]

import numpy as np
import cv2
# import psutil
import threading as th
from itertools import product, permutations
from random import randrange

from sys import getsizeof as gso


class CompImg:
    def __init__(self, image=None):
        self.timelapses = None
        self.currentcomposite = None
        self.limit = 699
        self.top = self.limit // 10
        self.min = 100
        self.divthresh = 30000
        self.noisethreshold = 15
        self.groomamount = 34
        if image:
            self.addpic(image)
        self.avgtoplevel = True
        self.orderkeyword = "order"

    def __sizeof__(self):  # quick and dirty size function
        return sum([gso(x) for x in [self.timelapses, self.currentcomposite]])

    def newpic(self, image):
        if isinstance(image, tuple):
            return np.zeros(image, dtype="uint8")
        return np.zeros(image.shape, dtype="uint8")

    def addpic(self, image):
        self.processpic(image)

    def comppic(self):
        if self.currentcomposite:
            return self.currentcomposite
        raise ValueError(
            "No pictures have been added.\nUse {self}.addpic() to add an image")

    def converttonparray(self, nparray):
        return np.asarray(nparray, dtype="uint8")

    def ismotion(self, image):
        diffs = np.where(self.absdiff(image) > 50)
        if diffs.shape[0].size > 1000:
            return

    def absdiff(self, image, outputimg=None):
        if outputimg is None:
            return cv2.absdiff(self.currentcomposite, image)
        cv2.absdiff(self.currentcomposite, image, outputimg)
        return outputimg

    def processpic(self, image):
        self.timelapses = self.taketimelapses(self.timelapses, image)
        self.groomtimelapses()
        self.currentcomposite = self.makecomposite(self.timelapses)

    def checkdepth(self, pic):
        counter = 0
        while isinstance(pic, list):
            pic = pic[0]
            counter += 1
            if isinstance(pic, dict):
                counter += 1
        return counter

    def taketimelapses(self, image, timelapse=None):
        if len(image.shape) != 3:
            raise ValueError("Image does not have a shape")
        if timelapse == None:
            if self.timelapses == None:
                self.timelapses = [image]
            else:
                self.timelapses.append(image)
            self.groomtimelapses()
            return self.timelapses
        return timelapse.append(image)

    def groomtimelapses(self, groomval=None):
        if groomval == None:
            groomval = self.timelapses

        if len(groomval) < 100:
            return groomval

        for i in groomval[:len(groomval) - 100]:
            np.where(groomval > 50)
            # if len(groomval) > len(self.avglimit):
            # trimlength = len(groomval) - self.avglimit
            # if trimlength > 0:
            #     groomval = groomval[trimlength:]
        return groomval

    # TODO: Fix so that once a value is clearly the most, it stops checking that pixel
    def makecomposite(self, timelapse=None):
        if timelapse is None:
            if self.timelapses is None:
                raise ValueError(
                    f"There are no timelapses. Run CompImg.taketimelapse() to get timelapses first")
            timelapse = self.timelapses
            isselftl = True
        else:
            isselftl = False

        if isinstance(timelapse, list):  # makes sure all lists are np.arrays
            timelapse = np.array(timelapse)
        if len(timelapse) == 1:  # if there's only one timelapse, return as composite
            composite = timelapse[0]
            if isselftl:
                self.currentcomposite = composite
            return composite

        diffs = []  # diffs between each picture
        diffaddress = {}

        for x in range(timelapse.shape[0] - 1):
            interval = int(len(timelapse) ** .5) * 4
            for y in range(x + 1, min(x + 50, x + interval, timelapse.shape[0])):
                diffs.append(np.array(np.where(cv2.absdiff(
                    timelapse[x], timelapse[y]) > self.noisethreshold)))
                for i in [x, y]:
                    if i in diffaddress:
                        diffaddress[i].append(len(diffs) - 1)
                    else:
                        diffaddress[i] = [len(diffs) - 1]
        diffs = sorted(diffs, key=lambda image: image.shape[0])

        timelapsescore = {}
        for i in diffaddress.keys():
            for j in diffaddress[i]:
                if j in timelapsescore:
                    timelapsescore[j] += diffs[i].shape[0]
                else:
                    timelapsescore[i] = diffs[i].shape[0]
        timelapseorder = sorted(list(timelapsescore.keys()),
                                key=lambda i: timelapsescore[i])

        if len(timelapseorder) > 10:
            # TODO: make this more precise
            timelapseorder = timelapseorder[:len(timelapseorder) // 3]
        elif len(timelapseorder) > 3:
            timelapseorder = timelapseorder[:len(timelapseorder) // 2]
        completed = []
        composite = timelapse[timelapseorder[0]]
        # tldiffs = [diffs[x] for x in diffaddress[timelapseorder[0]]]
        for g in timelapseorder[:1]:
            diff = cv2.absdiff(timelapse[g], composite)
            diffpoints = np.where(diff > self.noisethreshold)
            diffpntsarray = np.array(
                list(zip(diffpoints[0], diffpoints[1], diffpoints[2])), dtype='uint64')
            completedarray = np.array(completed, dtype='uint64')
            diffpntsfltr = np.where(
                diffpntsarray not in completedarray, diffpntsarray, None)
            for i in diffpntsfltr:
                i, j, k = i[0], i[1], i[2]
                completed.append([i, j, k])
                values = np.array(timelapse[:, i, j, k], dtype="uint8")
                composite[i][j][k] = self.neighbormax(values)
            # print(
            #     f"Percent adjusted = {float(diffpntsfltr[0].size)/float(composite.size)*100.0}%")
            print(
                f"{len(self.timelapses)} pictures are being used to calculate")
        if isselftl:
            self.currentcomposite = composite
        return composite

    def neighbormax(self, items):
        colors, counts = np.unique(items, return_counts=True)
        counts = [np.sum(np.where(colors[j] >= min(colors[i] - counts[i], 255) and colors[j] <=
                                  max(colors[i] + counts[i], 0))) for i, j in product(range(len(colors)), repeat=2)]
        maxcol = list(counts).index(max(counts))
        return maxcol

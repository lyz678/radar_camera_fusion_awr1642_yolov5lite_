import cv2
import time
import numpy as np
import onnxruntime as ort

class yolov5_lite():
    def __init__(self, model_pb_path, label_path, confThreshold=0.5, nmsThreshold=0.5):
        so = ort.SessionOptions()
        so.log_severity_level = 3
        self.net = ort.InferenceSession(model_pb_path, so)
        self.classes = list(map(lambda x: x.strip(), open(label_path, 'r').readlines()))

        self.confThreshold = confThreshold
        self.nmsThreshold = nmsThreshold
        self.input_shape = (self.net.get_inputs()[0].shape[2], self.net.get_inputs()[0].shape[3])

    def letterBox(self, srcimg, keep_ratio=True):
        top, left, newh, neww = 0, 0, self.input_shape[0], self.input_shape[1]
        if keep_ratio and srcimg.shape[0] != srcimg.shape[1]:
            hw_scale = srcimg.shape[0] / srcimg.shape[1]
            if hw_scale > 1:
                newh, neww = self.input_shape[0], int(self.input_shape[1] / hw_scale)
                img = cv2.resize(srcimg, (neww, newh), interpolation=cv2.INTER_AREA)
                left = int((self.input_shape[1] - neww) * 0.5)
                img = cv2.copyMakeBorder(img, 0, 0, left, self.input_shape[1] - neww - left, cv2.BORDER_CONSTANT,
                                         value=0)  # add border
            else:
                newh, neww = int(self.input_shape[0] * hw_scale), self.input_shape[1]
                img = cv2.resize(srcimg, (neww, newh), interpolation=cv2.INTER_AREA)
                top = int((self.input_shape[0] - newh) * 0.5)
                img = cv2.copyMakeBorder(img, top, self.input_shape[0] - newh - top, 0, 0, cv2.BORDER_CONSTANT, value=0)
        else:
            img = cv2.resize(srcimg, self.input_shape, interpolation=cv2.INTER_AREA)
        return img, newh, neww, top, left

    def postprocess(self, frame, outs, pad_hw):
        newh, neww, padh, padw = pad_hw
        frameHeight = frame.shape[0]
        frameWidth = frame.shape[1]
        ratioh, ratiow = frameHeight / newh, frameWidth / neww
        classIds = []
        confidences = []
        boxes = []
        for detection in outs:
            scores, classId = detection[4], detection[5]
            if scores > self.confThreshold:  # and detection[4] > self.objThreshold:
                x1 = int((detection[0] - padw) * ratiow)
                y1 = int((detection[1] - padh) * ratioh)
                x2 = int((detection[2] - padw) * ratiow)
                y2 = int((detection[3] - padh) * ratioh)
                classIds.append(classId)
                confidences.append(scores)
                boxes.append([x1, y1, x2, y2])

        # # Perform non maximum suppression to eliminate redundant overlapping boxes with
        # # lower confidences.
        indices = cv2.dnn.NMSBoxes(boxes, confidences, self.confThreshold, self.nmsThreshold)

        return boxes, indices, classIds, confidences

    def drawPred(self, frame, classId, conf, x1, y1, x2, y2):
        # Draw a bounding box.
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), thickness=2)

        label = '%.2f' % conf
        text = '%s:%s' % (self.classes[int(classId)], label)

        # Display the label at the top of the bounding box
        labelSize, baseLine = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        y1 = max(y1, labelSize[1])
        cv2.putText(frame, text, (x1, y1 - 10), cv2.FONT_HERSHEY_TRIPLEX, 0.5, (0, 255, 0), thickness=1)
        return frame

    def detect(self, srcimg):
        img, newh, neww, top, left = self.letterBox(srcimg)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img.astype(np.float32) / 255.0
        blob = np.expand_dims(np.transpose(img, (2, 0, 1)), axis=0)

        t1 = time.time()
        outs = self.net.run(None, {self.net.get_inputs()[0].name: blob})[0]
        cost_time = time.time() - t1
        print(outs.shape)

        boxes, indices, classIds, confidences = self.postprocess(srcimg, outs, (newh, neww, top, left))
        for idx in indices:
            classId = classIds[idx]
            confidence = confidences[idx]
            class_info = f"Class: {self.classes[int(classId)]}"
            confidence_info = f"Confidence: {confidence:.2f}"
            box = boxes[idx]
            x1, y1, x2, y2 = box
            cv2.putText(srcimg, class_info, (x1+10, y1+20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
            cv2.putText(srcimg, confidence_info, (x1+10, y1 + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
            cv2.rectangle(srcimg, (x1, y1), (x2, y2), (0, 0, 255), 2)

        infer_time = 'Inference Time: ' + str(int(cost_time * 1000)) + 'ms'
        print(infer_time)
        cv2.putText(srcimg, infer_time, (5, 20), cv2.FONT_HERSHEY_TRIPLEX, 0.5, (0, 0, 0), thickness=1)
        return srcimg


if __name__ == '__main__':
    imgpath = 'zidane.jpg'
    modelpath = 'v5lite-e_end2end.onnx'
    classfile = 'coco.names'
    confThreshold = 0.5
    nmsThreshold = 0.6
    net = yolov5_lite(modelpath, classfile, confThreshold=confThreshold, nmsThreshold=nmsThreshold)
    srcimg = cv2.imread(imgpath)
    net = yolov5_lite(modelpath, classfile, confThreshold=confThreshold, nmsThreshold=nmsThreshold)
    srcimg = net.detect(srcimg.copy())

    cv2.imwrite('save.jpg', srcimg )

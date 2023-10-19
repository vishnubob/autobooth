import logging
import time
import collections
import numpy as np
import multiprocessing as mp
from PIL import Image
from ultralytics import YOLO
from zero import ZeroServer

app = ZeroServer(port=5559)

class PeopleCounter:
    def __init__(self, window_size, max_people=10, false_positive_rate=0.1, false_negative_rate=0.1):
        # Store the last `window_size` observations
        self.observations = collections.deque(maxlen=window_size)
        
        # Maximum number of people that could be in the scene
        self.max_people = max_people

        # P( detection | person present)
        self.detection_prob_given_person = 1.0 - false_negative_rate
        
        # P( detection | person not present)
        self.detection_prob_given_no_person = false_positive_rate

        # Prior beliefs about the number of people present
        self.prior = np.ones(self.max_people + 1) / (self.max_people + 1)

    def add_observation(self, confidence_list):
        self.observations.append(confidence_list)

    def get_count(self):
        # Start with prior beliefs about the number of people
        posterior = self.prior.copy()

        # Update beliefs based on each observation
        for confidence_list in self.observations:
            likelihoods = self.compute_likelihoods(confidence_list)
            unnormalized_posterior = likelihoods * posterior
            
            # Normalize to ensure that the posterior probabilities sum to 1
            # And handle the case where the sum is zero separately
            sum_posterior = sum(unnormalized_posterior)
            if sum_posterior > 0:
                posterior = unnormalized_posterior / sum_posterior
            else:
                # If no hypotheses are supported by the data,
                # retain the prior distribution or use a uniform distribution.
                # Here we choose to retain the prior.
                pass 
            
        # Return the most likely number of people
        return np.argmax(posterior)

    def compute_likelihoods(self, confidence_list):
        likelihoods = np.zeros(self.max_people + 1)

        for n in range(self.max_people + 1):
            for confidence in confidence_list:
                # Compute the likelihood of observing this confidence value
                # given that there are `n` people in the scene.
                # This calculation could depend on your specific context.
                likelihoods[n] += self.compute_likelihood(confidence, n)
        
        return likelihoods

    def compute_likelihood(self, confidence, n):
        # A simple model might assume that each detection is independent given
        # the number of people, and might multiply the likelihoods for each detection.
        #
        # P( Detections | n people ) = product( P( Detection_i | n people ) )
        #
        # But here, due to the page length and complexity of the problem,
        # an exact likelihood computation would require more details and context about
        # how the confidence values are generated and how they correlate with actual
        # detections. This would be a quite complex function involving calculating
        # the likelihood for all possible configurations of people.
        
        # To simplify, here is an illustrative placeholder code.
        # In practice, you would replace this with a more sophisticated calculation
        # based on your understanding of how the confidence values are generated.
        if n == 0:
            return confidence * self.detection_prob_given_no_person
        else:
            return confidence * self.detection_prob_given_person

def run_yolo(person_count):
    logging.getLogger('ultralytics').setLevel(logging.WARN)
    host = 'yolo.lan'
    base_url = f'https://{host}'
    image_url = f'{base_url}/cgi-bin/currentpic.cgi'
    image_fn = 'capture.jpg'
    model_fn = 'yolov8n.pt'
    person_cls = 0
    conf_cutoff = 0.4

    rtsp_url = f'rtsp://{host}:8554/unicast'

    model = YOLO(model_fn)

    fps = 5
    delay = 1 / fps
    window_time_length_secs = 5
    window_length = window_time_length_secs * fps
    last_ma_count = 0
    results = model(rtsp_url, stream=True)

    counter = PeopleCounter(window_size=window_length)
    last_read = time.time()
    read_cycle = 1

    while True:
        for result in results:
            now = time.time()
            result = result.cpu().numpy()
            cls_conf = list(zip(result.boxes.cls, result.boxes.conf))
            conf_list = [it[1] for it in cls_conf if (it[0] == person_cls)]
            counter.add_observation(conf_list)
            if (time.time() - last_read) >= read_cycle:
                ma_count = counter.get_count()
                #print(f'{ma_count} humans')
                if ma_count != last_ma_count:
                    person_count.value = ma_count
                    print(f'{ma_count} humans')
                    last_ma_count = ma_count
                last_read = time.time()
            sleep_delay = delay - (time.time() - now)
            if sleep_delay:
                time.sleep(sleep_delay)

class YoloWorker(mp.Process):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.person_count = mp.Value('i', 0)

    def get_person_count(self):
        return self.person_count.value

    def run(self):
        print('Starting YOLO')
        run_yolo(self.person_count)

@app.register_rpc
def get_person_count() -> int:
    return app.yolo_worker.get_person_count()

if __name__ == "__main__":
    app.yolo_worker = YoloWorker()
    app.yolo_worker.start()
    app.run(workers=1)

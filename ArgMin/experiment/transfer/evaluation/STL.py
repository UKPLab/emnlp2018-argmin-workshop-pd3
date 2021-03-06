from __future__ import division

import math
from collections import OrderedDict

import numpy as np
from sklearn.metrics import accuracy_score, f1_score

import experiment


class SentenceClassificationSTLEvaluation(experiment.Evaluation):
    def __init__(self, config, config_global, logger):
        super(SentenceClassificationSTLEvaluation, self).__init__(config, config_global, logger)
        self.batchsize_test = self.config.get('batchsize_test', 512)
        self.report_accuracy = self.config.get('report_accuracy', False)

    def start(self, model, data, sess, valid_only=False, mode=None):
        results = OrderedDict()

        valid_accuracy, valid_f1 = self.evaluate(model, sess, data, data.archive.dev, mode=None)
        self.logger.debug('Results Valid: Accuracy={}, F1={}'.format(valid_accuracy, valid_f1))
        results['valid'] = valid_f1

        if not valid_only:
            # also validate on test
            for language, test in data.archive.test.items():
                test_accuracy, test_f1 = self.evaluate(model, sess, data, test, mode)
                results['test-{}'.format(language)] = test_accuracy if self.report_accuracy else test_f1
                self.logger.debug('Results Test ({}): Accuracy={}, F1={}'.format(language, test_accuracy, test_f1))

        return results

    def evaluate(self, model, sess, data, test, mode):
        split_sentences, split_labels = data.get_items(test)

        predictions = []
        for test_batch in range(int(math.ceil(len(split_sentences) / float(self.batchsize_test)))):
            test_batch_indices = self.batchsize_test * test_batch, self.batchsize_test * (test_batch + 1)
            test_batch_sentences = split_sentences[test_batch_indices[0]:test_batch_indices[1]]
            prediction, = sess.run([model.predict], feed_dict={
                model.input_sentence: test_batch_sentences,
                model.dropout_keep_prob: 1.0,
            })
            predictions += prediction.tolist()

        labels_flat = np.argmax(split_labels, axis=1)
        predictions_flat = np.argmax(predictions, axis=1)
        accuracy = accuracy_score(labels_flat, predictions_flat)
        assert len(labels_flat) == len(predictions_flat)

        f1 = f1_score(labels_flat, predictions_flat, average='macro')

        if self.config.get('output') is not None and mode is not None:
            with open('{}/{}'.format(self.config.get('output'), mode), 'w') as f:
                f.write('correct?, prediction, label, text\n')
                for l, p, t in zip(labels_flat, predictions_flat, test):
                    f.write('{}\t{}\t{}\t{}\n'.format(('correct' if l == p else 'wrong'), data.classes[p],data.classes[l], ' '.join(t[0])))

        return accuracy, f1


component = SentenceClassificationSTLEvaluation

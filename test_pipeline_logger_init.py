import os
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(SCRIPT_DIR, 'src')
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import recommender.feed_pipeline as fp


class PipelineLoggerInitTest(unittest.TestCase):
    def test_get_pipeline_logger_thread_safe_single_file_handler(self):
        # reset global logger state for isolated test
        if fp._pipeline_logger is not None:
            for h in list(fp._pipeline_logger.handlers):
                fp._pipeline_logger.removeHandler(h)
                try:
                    h.close()
                except Exception:
                    pass
        fp._pipeline_logger = None

        def get_logger_id(_):
            return id(fp._get_pipeline_logger())

        ids = []
        with ThreadPoolExecutor(max_workers=12) as ex:
            futures = [ex.submit(get_logger_id, i) for i in range(40)]
            for f in as_completed(futures):
                ids.append(f.result())

        logger = fp._get_pipeline_logger()
        file_handlers = [h for h in logger.handlers if h.__class__.__name__ == 'FileHandler']

        self.assertEqual(1, len(set(ids)))
        self.assertEqual(1, len(file_handlers))


if __name__ == '__main__':
    unittest.main()

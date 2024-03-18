import threading
import multiprocessing
import time
from tabulate import tabulate
from pathlib import Path


class KeywordFileSearcher:
    def __init__(self, directory_path, keywords):
        self.directory_path = directory_path
        self.keywords = keywords
        self.results = {}

    def reset_results(self):
        self.results = {}

    def find_files(self):
        return [
            str(file) for file in Path(self.directory_path).rglob("*") if file.is_file()
        ]

    def search_files(self, file_paths, keywords, results_queue, lock=None):
        local_result = {}
        for file_path in file_paths:
            try:
                with open(file_path, "r") as file:
                    content = file.read()
                    for keyword in keywords:
                        if keyword in content:
                            if keyword in local_result:
                                local_result[keyword].append(file_path)
                            else:
                                local_result[keyword] = [file_path]
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")

        if results_queue is not None:
            results_queue.put(local_result)
        else:
            if lock:
                with lock:
                    self.update_results(local_result)
            else:
                self.update_results(local_result)

    def update_results(self, local_result):
        for keyword, paths in local_result.items():
            if keyword in self.results:
                self.results[keyword].extend(paths)
            else:
                self.results[keyword] = paths

    def threaded_search(self, file_paths):
        self.reset_results()
        num_threads = 4
        threads = []
        lock = threading.Lock()

        for i in range(num_threads):
            thread_files = file_paths[i::num_threads]
            thread = threading.Thread(
                target=self.search_files,
                args=(thread_files, self.keywords, None, lock),
            )
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        return self.results

    def process_search(self, file_paths):
        self.reset_results()
        num_processes = 4
        processes = []
        results_queue = multiprocessing.Queue()

        for i in range(num_processes):
            process_files = file_paths[i::num_processes]
            process = multiprocessing.Process(
                target=self.search_files,
                args=(process_files, self.keywords, results_queue),
            )
            processes.append(process)
            process.start()

        for _ in range(num_processes):
            self.update_results(results_queue.get())

        for process in processes:
            process.join()

        return self.results


def pretty_print_results(title, results, duration):
    print(title)
    table = [[keyword, ", ".join(paths)] for keyword, paths in results.items()]
    print(
        tabulate(table, headers=["Keyword", "Files"], tablefmt="grid", maxcolwidths=50)
    )
    print("Час виконання:", duration)


if __name__ == "__main__":
    directory_path = "data"
    keywords = ["сила", "чорт", "любов"]

    searcher = KeywordFileSearcher(directory_path, keywords)

    file_paths = searcher.find_files()

    start_time = time.time()
    threaded_results = searcher.threaded_search(file_paths)
    threaded_duration = time.time() - start_time
    pretty_print_results(
        "Пошук з використанням потоків:", threaded_results, threaded_duration
    )

    print("")
    start_time = time.time()
    process_results = searcher.process_search(file_paths)
    process_duration = time.time() - start_time
    pretty_print_results(
        "Пошук з використанням мультипроцесингу:", process_results, process_duration
    )

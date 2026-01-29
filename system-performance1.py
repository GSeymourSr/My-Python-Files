import psutil
import time
import datetime

def get_system_performance():
    """
    Retrieves CPU and memory usage.

    Returns:
        tuple: (cpu_percent, memory_percent)
    """
    cpu_percent = psutil.cpu_percent(interval=1)  # Get CPU usage over 1 second
    memory_percent = psutil.virtual_memory().percent
    return cpu_percent, memory_percent

def log_performance(log_file="system_performance.log", interval=60):
    """
    Monitors and logs system performance at specified intervals.

    Args:
        log_file (str): Path to the log file.
        interval (int): Logging interval in seconds.
    """
    try:
        with open(log_file, "a") as f: # Use 'a' for append mode.
            while True:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cpu, mem = get_system_performance()
                log_entry = f"{timestamp}, CPU: {cpu}%, Memory: {mem}%\n"
                f.write(log_entry)
                print(log_entry.strip()) # Also print to console
                time.sleep(interval)

    except KeyboardInterrupt:
        print("\nMonitoring stopped.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    log_performance() # default interval is 60 seconds
    #log_performance(interval=30) # Example of changing the interval to 30 seconds
    #log_performance(log_file="my_custom_log.txt") # Example of changing the log filename.
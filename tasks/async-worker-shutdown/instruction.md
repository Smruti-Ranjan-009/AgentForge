The shutdown path cancels the worker task too early and never waits for pending work to finish. Restore graceful shutdown behavior without modifying the test harness.

# How to contribute a learner

Your learner should implement `learn.base.Learner`, and hence should
implement `fit`, `save_implementation`, and `report`.  Preferably each
learner will be in its own Python file.  The RoteLearner in
baselines.py is an example.

* `fit` will be the most time-intensive part of the learner, and will
  compute and save any sufficient statistics.
* `save_implementation` saves config info for the learned
  implementation, as a sample yaml data that shows how to configure
  the learned implementation, and all files needed to construct that
  implementation.
* `report` returns a human-readable string to help a user decide how
  successful the learning was.`

## Tracking provenance

Use the `collect_distillation_data` to collect training data from
recordings.  This saves the data in a learner-specific output
directory along with its provenance.  **If you need more
functionality, like retaining only successful traces**, extend the
code in `base`.

## Outputting code

If the code is possibly insecure than wrap it in LocalPythonExecutor.

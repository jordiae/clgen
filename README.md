Fork of https://github.com/fivosts/clgen. While the original software has many features, I just use it to dump C Github code from BigQuery into an SQLite database. With respect to the original code to get Github C repos, I modified it to also include header files (.h) and keep the repo stars as a field. Steps:

1. Clone this repo.
2. Run requirements.apt to install system dependencies (basically, we need an up-to-date version of CMake, Protobuf, etc).
3. Install Python requirements (requirements.txt).
4. Build: mkdir build && cd build && cmake .. && make
4. Get BigQuery credentials. The path to the credentials JSON is specified here: https://github.com/jordiae/clgen/blob/master/model_zoo/github/bq_C_db.pbtxt#L5
5. Run: ./clgen --config model_zoo/github/bq_C_db.pbtxt

(Original README below)

<div align="center">
  <a href="https://github.com/ChrisCummins/phd/tree/master/deeplearning/clgen">
    <img src="https://raw.githubusercontent.com/ChrisCummins/phd/master/deeplearning/clgen/docs/assets/logo.png" width="420">
  </a>
</div>

-------

<div align="center">
  <!-- Better code -->
  <a href="https://bettercodehub.com/results/ChrisCummins/clgen">
    <img src="https://bettercodehub.com/edge/badge/ChrisCummins/clgen?branch=master">
  </a>
  <!-- License -->
  <a href="https://www.gnu.org/licenses/gpl-3.0.en.html" target="_blank">
    <img src="https://img.shields.io/badge/license-GNU%20GPL%20v3-blue.svg?style=flat">
  </a>
  <!-- CircleCI -->
  <a href="https://circleci.com/gh/fivosts/clgen">
    <img src="https://circleci.com/gh/fivosts/clgen.svg?style=svg&circle-token=970ffce3c85304ccd182c59fb969504efe646ef6">
  </a>
</div>

**CLgen** is an open source application for generating runnable programs using
deep learning. CLgen *learns* to program using neural networks which model the
semantics and usage from large volumes of program fragments, generating
many-core OpenCL programs that are representative of, but *distinct* from, the
programs it learns from.

<img src="https://raw.githubusercontent.com/ChrisCummins/phd/master/deeplearning/clgen/docs/assets/pipeline.png" width="500">


## Install CLGEN

TODO!


#### What next?

CLgen is a tool for generating source code. How you use it will depend entirely
on what you want to do with the generated code. As a first port of call I'd
recommend checking out how CLgen is configured. CLgen is configured through a
handful of
[protocol buffers](https://developers.google.com/protocol-buffers/) defined in
[//deeplearning/clgen/proto](/deeplearning/clgen/proto).
The [clgen.Instance](/deeplearning/clgen/proto/clgen.proto) message type
combines a [clgen.Model](/deeplearning/clgen/proto/model.proto) and
[clgen.Sampler](/deeplearning/clgen/proto/sampler.proto) which define the
way in which models are trained, and how new programs are generated,
respectively. You will probably want to assemble a large corpus of source code
to train a new model on - I have [tools](/datasets/github/scrape_repos) which
may help with that. You may also want a means to execute arbitrary generated
code - as it happens I have [tools](/gpu/cldrive) for that too. :-) Thought of a
new use case? I'd love to hear about it!


## Resources

Presentation slides:

<a href="https://speakerdeck.com/chriscummins/synthesizing-benchmarks-for-predictive-modelling-cgo-17">
  <img src="https://raw.githubusercontent.com/ChrisCummins/phd/master/deeplearning/clgen/docs/assets/slides.png" width="500">
</a>

Publication
["Synthesizing Benchmarks for Predictive Modeling"](https://github.com/ChrisCummins/paper-synthesizing-benchmarks)
(CGO'17).

[Jupyter notebook](https://github.com/ChrisCummins/paper-synthesizing-benchmarks/blob/master/code/Paper.ipynb)
containing experimental evaluation of an early version of CLgen.

My documentation sucks. Don't be afraid to get stuck in and start
[reading the code!](deeplearning/clgen/clgen.py)

## License

Copyright 2016-2020 Chris Cummins <chrisc.101@gmail.com>.

Released under the terms of the GPLv3 license. See
[LICENSE](/deeplearning/clgen/LICENSE) for details.

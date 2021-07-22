"""
Feature space sampling of source code.
"""
import typing
import tempfile
import contextlib
import pathlib
import math
import subprocess

from deeplearning.clgen.features import extractor
from deeplearning.clgen.features import normalizers
from deeplearning.clgen.preprocessors import opencl
from eupy.native import logger as l

from absl import flags
from eupy.native import logger as l

FLAGS = flags.FLAGS

targets = {
  'rodinia': './benchmarks/rodinia_3.1.tar.bz2',
  'grid_walk': '',
}

@contextlib.contextmanager
def GetContentFileRoot(path: pathlib.Path) -> typing.Iterator[pathlib.Path]:
  """
  Extract tar archive of benchmarks and yield the root path of all files.

  Yields:
    The path of a directory containing content files.
  """
  with tempfile.TemporaryDirectory(prefix=path.stem) as d:
    cmd = [
      "tar",
      "-xf",
      str(path),
      "-C",
      d,
    ]
    subprocess.check_call(cmd)
    yield pathlib.Path(d)

def iter_cl_files(path: pathlib.Path) -> typing.List[str]:
  """
  Iterate base path and yield the contents of all .cl files.
  """
  contentfiles = []
  with GetContentFileRoot(path) as root:
    file_queue = [p for p in root.iterdir()]
    while file_queue:
      c = file_queue.pop(0)
      if c.is_symlink():
        continue
      elif c.is_dir():
        file_queue += [p for p in c.iterdir()]
      elif c.is_file() and c.suffix == ".cl":
        with open(c, 'r') as inf:
          contentfiles.append((c, inf.read()))
  return contentfiles

def yield_cl_kernels(path: pathlib.Path) -> typing.List[typing.Tuple[pathlib.Path, str]]:
  """
  Fetch all cl files from base path and atomize, preprocess
  kernels to single instances.
  """
  contentfiles = iter_cl_files(path)
  kernels = []
  for p, cf in contentfiles:
    ks = opencl.ExtractOnlySingleKernels(
          opencl.InvertKernelSpecifier(
          opencl.StripDoubleUnderscorePrefixes(cf)))
    for k in ks:
      kernels.append((p, k))
  return kernels

def calculate_distance(infeat: typing.Dict[str, float],
                       tarfeat: typing.Dict[str, float],
                       feature_space: str,
                       ) -> float:
  """
  Euclidean distance between sample feature vector
  and current target benchmark.
  """
  d = 0
  for key in tarfeat.keys():
    n = normalizers.normalizer[feature_space][key]
    i = infeat[key] / n
    t = tarfeat[key] / n
    d += abs((t**2) - (i**2))
  return math.sqrt(d)

class EuclideanSampler(object):
  """
  This is a shitty experimental class to work with benchmark comparison.
  Will be refactored obviously.
  """
  class Benchmark(typing.NamedTuple):
    path: pathlib.Path
    name: str
    contents: str
    feature_vector: typing.Dict[str, float]

  def __init__(self,
               workspace: pathlib.Path,
               feature_space: str,
               target: str
               ):
    self.target = target
    if self.target != "grid_walk":
      self.path        = pathlib.Path(targets[target]).resolve()
    self.workspace     = workspace
    self.feature_space = feature_space
    self.loadCheckpoint()
    try:
      self.target_benchmark = self.benchmarks.pop(0)
      l.getLogger().info("Target benchmark: {}\nTarget fetures: {}".format(self.target_benchmark.name, self.target_benchmark.feature_vector))
    except IndexError:
      self.target_benchmark = None
    return

  def iter_benchmark(self):
    """
    When it's time, cycle through the next target benchmark.
    """
    # self.benchmarks.append(self.benchmarks.pop(0))
    try:
      self.target_benchmark = self.benchmarks.pop(0)
    except IndexError:
      self.target_benchmark = None
    self.saveCheckpoint()
    l.getLogger().info("Target benchmark: {}\nTarget fetures: {}".format(self.target_benchmark.name, self.target_benchmark.feature_vector))
    return

  def calculate_distance(self, infeat: typing.Dict[str, float]) -> float:
    """
    Euclidean distance between sample feature vector
    and current target benchmark.
    """
    return calculate_distance(infeat, self.target_benchmark.feature_vector, self.feature_space)

  def topK_candidates(self,
                      candidates: typing.List[typing.TypeVar("ActiveSample")],
                      K : int,
                      ) -> typing.List[typing.TypeVar("ActiveSample")]:
    """
    Return top-K candidates.
    """
    return sorted(candidates, key = lambda x: x.score)[:K]

  def sample_from_set(self, 
                      candidates: typing.List[typing.TypeVar("ActiveSample")],
                      search_width: int,
                      ) -> bool:
    """
    Find top K candidates by getting minimum
    euclidean distance from set of rodinia benchmarks.
    """
    """
    for idx in range(len(candidates)):
      candidates[idx] = candidates[idx]._replace(
        score = self.calculate_distance(candidates[idx].features)
      )
    """
    return self.topK_candidates(candidates, search_width)

  def saveCheckpoint(self) -> None:
    """
    Save feature sampler state.
    """
    with open(self.workspace / "feature_sampler_state.pkl", 'wb') as outf:
      pickle.dump(self.benchmarks, outf)
    return


  def loadCheckpoint(self) -> None:
    """
    Load feature sampler state.
    """
    if (self.workspace / "feature_sampler_state.pkl").exists():
      with open(self.workspace / "feature_sampler_state.pkl", 'rb') as infile:
        self.benchmarks = pickle.load(infile)
    else:
      self.benchmarks = []
      if self.target == "grid_walk":
        # have a MAX vector for each feature of each feature space
        # and create empty benchmarks with said iterated vectors
        raise NotImplementedError
      else:
        kernels = yield_cl_kernels(self.path)
        for p, k in kernels:
          features = extractor.ExtractFeatures(k, [self.feature_space])
          if features[self.feature_space]:
            self.benchmarks.append(
              EuclideanSampler.Benchmark(
                  p,
                  p.name,
                  k,
                  features[self.feature_space],
                )
            )
    l.getLogger().info("Loaded {}, {} benchmarks".format(self.target, len(self.benchmarks)))
    l.getLogger().info(', '.join([x for x in set([x.name for x in self.benchmarks])]))
    return

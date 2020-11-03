import subprocess
import tempfile

from deeplearning.clgen.util import environment
from deeplearning.clgen.util import crypto

CLGEN_FEATURES = environment.CLGEN_FEATURES
CLGEN_REWRITER = environment.CLGEN_REWRITER

def kernel_features(src: str, *extra_args) -> str:
  """
  Invokes clgen_features extractor on a single kernel.

  Params:
    src: (str) Kernel in string format.
    extra_args: Extra compiler arguments passed to feature extractor.
  Returns:
    Feature vector and diagnostics in str format.
  """
  if file_name:
    tfile = lambda: open("/tmp/{}.cl".format(file_name), 'w')
  else:
    tfile = lambda: tempfile.NamedTemporaryFile(
      'w', prefix = "feature_extractor_", suffix = '.cl'
    )
    
  file_hash = crypto.sha256_str(src)
  with tempfile.NamedTemporaryFile(
          'w', prefix = "feat_ext_{}_".format(file_hash), suffix = '.cl'
        ) as f:
    f.write(src)
    f.flush()
    cmd = [str(CLGEN_FEATURES), f.name]

    process = subprocess.Popen(
      cmd,
      stdout = subprocess.PIPE,
      stderr = subprocess.PIPE,
      universal_newlines = True,
    )
    stdout, stderr = process.communicate()
  return stdout

def StrToDictFeatures(str_features: str) -> typing.Dict[str, float]:
  """
  Converts clgen_features subprocess output from raw string
  to a mapped dictionary of feature -> value.
  """
  try:
    lines  = str_features.split('\n')
    header, values = lines[0].split(',')[2:], lines[-1].split(',')[2:]
    if len(header) != len(values):
      raise ValueError("Bad alignment of header-value list of features")
    return {key: float(value) for key, value in zip(header, values)}
  except Exception as e:
    raise ValueError(e)

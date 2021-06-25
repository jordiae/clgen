"""
Feature Extraction module for LLVM InstCount pass.
"""
import subprocess
import tempfile
import typing

from deeplearning.clgen.preprocessors import opencl
from deeplearning.clgen.util import environment

from eupy.hermes import client

INSTCOUNT = "-load {} -InstCount".format(environment.INSTCOUNT)

class InstCountFeatures(object):
  """
  70-dimensional LLVM-IR feature vector,
  describing Total Funcs, Total Basic Blocks, Total Instructions
  and count of all different LLVM-IR instruction types.
  """
  def __init__(self):
    return

  @classmethod
  def ExtractFeatures(cls, src: str) -> typing.Dict[str, float]:
    return cls.RawToDictFeats(cls.ExtractRawFeatures(src))

  @classmethod
  def ExtractRawFeatures(cls, src: str) -> str:
    return opencl.CompileOptimizer(src, INSTCOUNT)

  @classmethod
  def RawToDictFeats(cls, str_feats: str) -> typing.Dict[str, float]:
    return {feat.split(' : ')[0]: int(feat.splt(' : ')[1]) for feat in str_feats.split('\n') if ' : ' in feat}

# Copyright (c) 2016-2020 Chris Cummins.
#
# clgen is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# clgen is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with clgen.  If not, see <https://www.gnu.org/licenses/>.
"""This file contains the definition of atomizers.

An atomizer converts a block of text into a sequence of vocbulary tokens.
"""
import pathlib
import pickle
import typing
import json
import numpy as np
from collections import Counter
from absl import flags
from eupy.native import logger as l

FLAGS = flags.FLAGS

def FromText(config, corpus_txt: str):
  mask_tokens = False if config.mask_tokens is None else config.mask_tokens

  if config.token_type   == "character":
    if config.token_list is not None:
      l.getLogger().warning("token list in character-based tokenization is going to be ignored.")
    return AsciiCharacterAtomizer.FromText(corpus_txt, mask_tokens)
  elif config.token_type == "word":
    with open(config.token_list, 'r') as f:
      token_set = json.load(f)
      token_set = set(token_set['opencl']['tokens'])
    wpc_tok = False if config.wordpiece_tokenization is None else config.wordpiece_tokenization

    return WordAtomizer.FromText(corpus_txt,
                                 token_set, 
                                 mask_tokens, 
                                 wpc_tok
                                )
  else:
    raise NotImplementedError

class AtomizerBase(object):
  """The base class for implementing atomizers."""

  def __init__(self, 
               vocab: typing.Dict[str, int],
               metaTokens: typing.Dict[str, str]
               ):
    """Instantiate an atomizer.

    Args:
      vocab: A dictionary of mappings from character sequences (atoms) into
        indices.
      metaTokens: A dictionary mapping the metaTokens needed for tokenization.
        (Used when masking is selected)
    Raises:
      TypeError: If vocab is not a dictionary.
      ValueError: If the dictionary of mappings includes any duplicate values.
    """
    self.vocab      = vocab
    self.metaTokens = metaTokens
    self._UpdateVocabulary()

  @property
  def atoms(self) -> typing.List[str]:
    """A list of atoms in the vocabulary."""
    return list(sorted(self.vocab.keys()))

  @property
  def indices(self) -> typing.List[int]:
    """A list of vocabulary indices."""
    return list(sorted(self.vocab.values()))

  def _UpdateVocabulary(self) -> None:
    """Private method which must be called if vocab is modified."""
    if not isinstance(self.vocab, dict):
      raise TypeError("vocabulary must be a dict")

    # Each atom and index must be unique to ensure deterministic encoding.
    if len(set(self.vocab.keys())) != len(self.vocab):
      raise ValueError("all atoms must be unique")
    if len(set(self.vocab.values())) != len(self.vocab):
      raise ValueError("all indices must be unique")

    self.vocab_size = len(self.vocab)
    self.decoder = {val: key for key, val in self.vocab.items()}
    # Set arbitrary object properties for meta tokens.
    self.__dict__.update({x: self.vocab[y] for x, y in self.metaTokens.items()})

  def AtomizeString(self, text: str) -> np.array:
    """Atomize a text into an array of vocabulary indices.

    Args:
      text: Input text.

    Returns:
      An array of indices into vocabulary for all atoms in text.

    Raises:
      VocabError: If the input text contains elements not in the vocabulary.
    """
    raise NotImplementedError("abstract class")

  def TokenizeString(self, text: str) -> typing.List[str]:
    """Split the text into atoms, but do not encode to indices.

    Args:
      text: Input text.

    Returns:
      A list of tokens.
    """
    indices = self.AtomizeString(text)
    return list(map(lambda x: self.decoder[x], indices))

  def DeatomizeIndices(self, 
                       encoded: np.array, 
                       ignore_token: int = None):
    """Translate atomized code back into a string.

    Args:
      encoded: An nparray of encoded vocabulary indices.
      ignore_token: A specific token to ignore from the text string (e.g. exclude pads)
    Returns:
      The decoded text.
      Returns string if nparray is one-dimensional.
      Else returns list for each extra dimension of strings.
    """
    try:
      if np.ndim(encoded) > 1:
        return [ self.DeatomizeIndices(x, ignore_token) for x in encoded ]
      elif np.ndim(encoded) == 1:
        return "".join(list(map(lambda x: self.decoder[x] if x != ignore_token else '', encoded)))
      else:
        raise ValueError("Wrong encoded array specified")
    except KeyError:
      raise KeyError("Out of vocab: {}".format(encoded))

  def ToFile(self, path: pathlib.Path) -> None:
    """Save an atomizer to file."""
    with open(path, "wb") as f:
      pickle.dump(self, f)

  @classmethod
  def FromText(cls, text: str) -> "AtomizerBase":
    """Instantiate and specialize an atomizer from a corpus text.

    Args:
      text: Text corpus

    Returns:
      An atomizer instance.
    """
    raise NotImplementedError("abstract class")

  @classmethod
  def FromFile(cls, path: pathlib.Path) -> "AtomizerBase":
    """Load an atomizer from file."""
    with open(path, "rb") as infile:
      return pickle.load(infile)


class AsciiCharacterAtomizer(AtomizerBase):
  """An atomizer for character-level syntactic modelling."""

  def AtomizeString(self, text: str) -> np.array:
    """Atomize a text into an array of vocabulary indices.

    Args:
      text: Input text.

    Returns:
      An array of indices into vocabulary for all atoms in text.
    """
    try:
      if not self.metaTokens:
        return np.array(list(map(lambda x: self.vocab[x], text)), dtype=np.int32)
      else:
        encoded = []
        skipNext = 0
        for idx, char in enumerate(text):
          if skipNext > 0:
            skipNext -= 1
            continue
          if char == '[':
            for meta in self.metaTokens.values():
              if text[idx: idx + len(meta)] == meta:
                encoded.append(self.vocab[meta])
                skipNext = len(meta) - 1
                break
          if skipNext == 0:
            encoded.append(self.vocab[char])
        return np.array(encoded, dtype = np.int32)
    except KeyError:
      raise ValueError("OoV index in string tokenizing.")
      
  def __repr__(self) -> str:
    return f"AsciiCharacterAtomizer[{self.vocab_size} chars]"

  @classmethod
  def FromText(cls, text: str, mask_tokens: bool) -> "AsciiCharacterAtomizer":
    """Instantiate and an atomizer from a corpus text.

    Args:
      text: Text corpus.

    Returns:
      An atomizer instance.
    """
    if mask_tokens:
      metaTokens = {
          'startToken'   : '[START]',
          'endToken'     : '[END]',
          'padToken'     : '[PAD]',
          'maskToken'    : '[MASK]',
          'holeToken'    : '[HOLE]',
          'endholeToken' : '[ENDHOLE]',
      }
    else:
      metaTokens = {}
    counter = Counter(text)
    count_pairs = sorted(counter.items(), key=lambda x: -x[1])
    atoms, _ = zip(*count_pairs)
    atoms = tuple(metaTokens.values()) + atoms
    vocab = dict(zip(atoms, range(len(atoms))))
    return AsciiCharacterAtomizer(vocab, metaTokens)

class WordAtomizer(AtomizerBase):
  """A greedy atomizer supports multi-character tokens."""

  def __init__(self, 
               vocab:      typing.Dict[str, int], 
               metaTokens: typing.Dict[str, str],
               determine_chars = False):
    super(WordAtomizer, self).__init__(vocab, metaTokens)

    self.determine_chars = determine_chars
    multichars = set(k for k in self.atoms if len(k) > 1)
    first_chars = set(a[0] for a in multichars)
    self.lookup = dict(
      (c, [a for a in multichars if a[0] == c]) for c in first_chars
    )

  def AtomizeString(self, text: str) -> np.array:
    """Atomize a text into an array of vocabulary indices.

    Args:
      text: Input text.

    Returns:
      An array of indices into vocabulary for all atoms in text.
    """

    def _AddToVocab(token: str) -> int:
      """Add a token to the vocabulary and return its index."""
      ## TODO this will crash if cond1 = False && cond2 = True.
      if self.determine_chars and token not in self.vocab:
        max_index = max(self.vocab.values())
        self.vocab[token] = max_index + 1
      return self.vocab[token]

    indices = []
    i = 0
    j = 2
    try:
      while i < len(text):
        if self.lookup.get(text[i]):
          if j <= len(text) and any(
            x.startswith(text[i:j]) for x in self.lookup[text[i]]
          ):
            j += 1
          else:
            while j > i + 1:
              if any(x == text[i:j] for x in self.lookup[text[i]]):
                indices.append(self.vocab[text[i:j]])
                i = j
                j += 2
                break
              else:
                j -= 1
            else:
              indices.append(_AddToVocab(text[i]))
              i += 1
              j += 2
        else:
          indices.append(_AddToVocab(text[i]))
          i += 1
          j += 2
    except KeyError:
      raise ValueError

    if self.determine_chars:
      self._UpdateVocabulary()

    return np.array(indices, dtype=np.int32)

  def __repr__(self) -> str:
    return f"WordAtomizer[{self.vocab_size} tokens]"

  @classmethod
  def FromText(cls, text: str, token_list: typing.Set[str], mask_tokens: bool, wordpiece: bool) -> "WordAtomizer":
    """Instantiate and an atomizer from a corpus text.

    Args:
      text: Text corpus
      token_list: A list of multi-character token_list.

    Returns:
      An atomizer instance.
    """
    if not token_list:
      raise ValueError("No tokens specified")

    if wordpiece:
      raise NotImplementedError

    if mask_tokens:
      metaTokens = {
          'startToken'   : '[START]',
          'endToken'     : '[END]',
          'padToken'     : '[PAD]',
          'maskToken'    : '[MASK]',
          'holeToken'    : '[HOLE]',
          'endholeToken' : '[ENDHOLE]',
      }
    else:
      metaTokens = {}
    # Add meta token_list to token set
    for mt in metaTokens.values():
      token_list.add(mt)
    # Instantiate a greedy atomizer using the full vocabulary.
    full_vocab = dict(zip(token_list, range(len(token_list))))
    c = WordAtomizer(full_vocab, metaTokens, determine_chars=True)
    # Derive the subset of the vocabulary required to encode the given text.
    tokens = [mt for mt in metaTokens.values()] + sorted(list(set(c.TokenizeString(text))))
    vocab_subset = dict(zip(tokens, range(len(tokens))))
    # Return a new atomizer using the subset vocabulary.
    return WordAtomizer(vocab_subset, metaTokens)

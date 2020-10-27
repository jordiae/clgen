"""Github mining configuration"""
import json
import os
import io
import re
import time
import requests
import sys
import typing
import pathlib
import github
import progressbar
import copy
import numpy as np

from base64 import b64decode
from functools import partial
from google.cloud import bigquery

from deeplearning.clgen.util import pbutil
from deeplearning.clgen.proto import github_pb2
from deeplearning.clgen.github import datasets
from deeplearning.clgen.github import storage
from deeplearning.clgen.github import bigQuery_database

from eupy.native import logger as l

class GithubMiner(object):
  """Base abstract class of a github miner"""

  @classmethod
  def FromConfig(cls, config: github_pb2.GithubMiner):
    """Constructs github miner from protobuf configuration."""
    try:
      pbutil.AssertFieldIsSet(config, "path")
      pbutil.AssertFieldIsSet(config, "data_format")
      pbutil.AssertFieldIsSet(config, "miner")

      if config.HasField("big_query"):
        pbutil.AssertFieldIsSet(config.big_query, "credentials")
        pbutil.AssertFieldConstraint(
          config.big_query,
          "language",
          lambda x: x in {'generic', 'opencl', 'c', 'cpp', 'java', 'python'},
          "language must be one of opencl, c, cpp, java, python. 'generic' for language agnostic queries.",
        )
        return BigQuery(config)
      elif config.HasField("recursive"):
        pbutil.AssertFieldIsSet(config.recursive, "access_token")
        pbutil.AssertFieldConstraint(
          config.recursive,
          "flush_limit_K",
          lambda x: x>0,
          "flush limit cannot be non-positive."
          )
        pbutil.AssertFieldConstraint(
          config.recursive,
          "corpus_size_K",
          lambda x: x >= -1,
          "corpus size must either be -1 or non-negative."
          )
        if config.data_format != github_pb2.GithubMiner.DataFormat.folder:
          raise NotImplementedError("RecursiveFetcher only stores files in local folder.")
        return RecursiveFetcher(config)
      else:
        raise SystemError("{} miner not recognized".format(config))
    except Exception as e:
      raise e

  def __init__(self):
    return

  def fetch(self) -> None:
    raise NotImplementedError("Abstract class")

class BigQuery(GithubMiner):
  def __init__(self,
               config: github_pb2.GithubMiner
               ):
    super(BigQuery, self).__init__()
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(pathlib.Path(config.big_query.credentials, must_exist = True))
    self.cache_path = pathlib.Path(config.path, must_exist = False).expanduser().resolve()
    self.cache_path.mkdir(exist_ok = True, parents = True)

    l.getLogger().info("Initializing BigQuery miner in {}".format(self.cache_path))
    job_config = bigquery.QueryJobConfig(allowLargeResults = True)
    job_config.allow_large_results = True
    self.client = bigquery.Client(default_query_job_config = job_config)

    self.dataset = datasets.Dataset.FromArgs(self.client, config.big_query.language)
    self.storage = storage.Storage.FromArgs(self.cache_path, self.dataset.name, self.dataset.extension, config.data_format)
    return

  def fetch(self):
    self._query_github()
    self._export_corpus()
    return

  def _query_github(self) -> None:
    """Apply bigQuery requests to get all contentfiles"""
    with self.storage as st:

      repos = st.db.main_repo_entries
      repos.update(st.db.other_repo_entries)
      l.getLogger().info(len(repos))

      # header_repos = st.db.header_repo_entries
      # final_repos = set()
      # for repo in repos:
      #   if repo not in header_repos:
      #     final_repos.add(repo)
      # l.getLogger().info(len(final_repos))

      # rep_list = [tuple(r.split(', ')) for r in final_repos]

      # total_header_rows = 0

      # header_includes_it = self.dataset.header_file_query(rep_list)
      # l.getLogger().warn(header_includes_it)
      # for i in header_includes_it:
      #   l.getLogger().info(i)
      # exit()
      # if header_includes_it:
      #   total_header_rows += header_includes_it.total_rows
      #   with progressbar.ProgressBar(max_value = header_includes_it.total_rows) as bar:
      #     for en, hf in enumerate(header_includes_it):
      #       st.save(bigQuery_database.bqHeaderFile(
      #           **bigQuery_database.bqHeaderFile.FromArgs(st.filecount, hf)
      #         )
      #       )
      #       bar.update(en)
      #   st.flush()        

      header_repos = st.db.header_repo_entries
      final_repos = set()
      with progressbar.ProgressBar(max_value = len(header_repos)) as bar:
        for repo in bar(header_repos):
          if repo in repos:
            final_repos.add(repo)
        l.getLogger().info(len(final_repos))

      cached_deletes = set()
      import copy
      new_db = bigQuery_database.bqDatabase("sqlite:///{}".format(self.cache_path / ("new_" + ".db")))

      with st.db.Session(commit = False) as session:
        for i in session.query(bigQuery_database.bqHeaderFile).yield_per(100000).enable_eagerloads(False):
          if "{}, {}".format(i.repo_name, i.ref) in final_repos:
            cached_deletes.add(i)
            print(len(cached_deletes))
          if len(cached_deletes) % 1000 == 0 and (len(cached_deletes) -1) > 0:
            bar = progressbar.ProgressBar(max_value = len(cached_deletes))
            with new_db.Session(commit = True) as s:
              for j in bar(cached_deletes):
                s.add(j)
              s.commit()
            cached_deletes = set()
        # q = session.query(bigQuery_database.bqHeaderFile
        #     ).filter("{}, {}".format(
        #       bigQuery_database.bqHeaderFile.repo_name, bigQuery_database.bqHeaderFile.ref
        #       ) in final_repos).delete()
        # session.commit()
        with new_db.Session(commit = True) as s:
          for j in cached_deletes:
            s.add(j)
          session.commit()
          cached_deletes = set()
      exit()
      main_repo_count  = 0
      other_repo_count = 0

      mainf_it, otherf_it = self.dataset.contentfile_query()
      if mainf_it:
        with progressbar.ProgressBar(max_value = mainf_it.total_rows, prefix = "Main Files") as bar:
          for en, mf in enumerate(mainf_it):
            st.save(bigQuery_database.bqMainFile(
                **bigQuery_database.bqMainFile.FromArgs(st.filecount, mf)
              )
            )
            bar.update(en)
        main_repo_count = st.repocount
        st.flush()

      if otherf_it:
        with progressbar.ProgressBar(max_value = otherf_it.total_rows, prefix = "Other Files") as bar:
          for en, of in enumerate(otherf_it):
            st.save(bigQuery_database.bqOtherFile(
                **bigQuery_database.bqOtherFile.FromArgs(st.filecount, of)
              )
            )
            bar.update(en)
        other_repo_count = st.repocount - main_repo_count
        st.flush()

      # Get repository list of requested file specifications.
      # If contentfile_query has taken place, use cached results instead of re-querying.
      if mainf_it or otherf_it:
        mainrep_it, otherrep_it = None, None
      else:
        mainrep_it, otherrep_it = self.dataset.repository_query()

      if mainrep_it:
        with progressbar.ProgressBar(max_value = mainrep_it.total_rows, prefix = "Main Repos") as bar:
          for en, mr in enumerate(mainrep_it):
            st.save(bigQuery_database.bqRepo(
                **bigQuery_database.bqRepo.FromArgs(st.repocount, mr)
              )
            )
            bar.update(en)
        main_repo_count = st.repocount
        st.flush()

      other_repo_count = 0
      if otherrep_it:
        with progressbar.ProgressBar(max_value = otherrep_it.total_rows, prefix = "Other Repos") as bar:
          for en, orep in enumerate(otherrep_it):
            st.save(bigQuery_database.bqRepo(
                **bigQuery_database.bqRepo.FromArgs(st.repocount, orep)
              )
            )
            bar.update(en)
        other_repo_count = st.repocount - main_repo_count
        st.flush()

      # Parse files from mined repos to get header files as well.
      repo_list = st.repoTuple
      np.random.shuffle(repo_list)
      # Split repo list into chunks of 1K, in order to do queries in steps that will not timeout (6 hrs).
      threshold = 500
      repolist_chunks = []

      t = threshold
      while True:
        repolist_chunks.append(repo_list[len(repolist_chunks) * threshold: t])
        t += threshold
        if t > len(repo_list):
          repolist_chunks.append(repo_list[len(repolist_chunks) * threshold:])
          break

      total_header_rows = 0
      for p, repo in enumerate(repolist_chunks):
        header_includes_it = self.dataset.header_file_query(repo)
        if header_includes_it:
          total_header_rows += header_includes_it.total_rows
          with progressbar.ProgressBar(max_value = header_includes_it.total_rows, prefix = "Header Files: {}".format(p)) as bar:
            for en, hf in enumerate(header_includes_it):
              st.save(bigQuery_database.bqHeaderFile(
                  **bigQuery_database.bqHeaderFile.FromArgs(st.filecount, hf)
                )
              )
              bar.update(en)
          st.flush()

      # Filecount of requested file specifications.
      # Use cached results if contentfile has taken place.
      if mainf_it or otherf_it:
        self.dataset.filecount = (mainf_it.total_rows if mainf_it else 0, otherf_it.total_rows if otherf_it else 0)
      mainfile_count, otherfile_count = self.dataset.filecount
      header_file_count = total_header_rows

      query_data = [
        "main_contentfiles : {}".format(mainfile_count),
        "other_contentfiles: {}".format(otherfile_count),
        "include_contentfiles: {}".format(header_file_count),
        "total_contentfiles: {}".format(mainfile_count + otherfile_count + header_file_count),
        "",
        "main_repositories : {}".format(main_repo_count),
        "other_repositories: {}".format(other_repo_count),
        "total_repositories: {}".format(main_repo_count + other_repo_count),
      ]
      st.save(bigQuery_database.bqData(key = self.dataset.name, value = '\n'.join(query_data)))
    return

  def _export_corpus(self) -> None:
    """
    Get all raw files requested from BQ and export them to CLGEN corpus.

    The most important aspect is inlining includes into the source files.

    In case the selected storage type is SQL DB, all needed header files
    will be found in bq_header_contentfiles table and will be drawn from there.
    The original storage DB can be diminished in size, by deleting the header
    files that were not eventually used.
    """
    export_storage = storage.Storage.FromArgs(
      self.cache_path,
      "exported_".format(self.dataset.name),
      self.dataset.extension,
      config.data_format
    )
    with export_storage as st:
      with progressbar.ProgressBar(
        max_value = self.storage.mainfile_count + self.storage.otherfile_count,
        prefix = "Inlining headers"
      ) as bar:
        for cf in bar(self.storage.main_contentfiles + self.storage.other_contentfiles):
          inlined_cf, inlined_headers = self._inline_headers(cf)
          for inl_cf in [inlined_cf] + inlined_headers:
            st.save(inl_cf)
    return

  def _inline_headers(self,
                      contentfile: bigQuery_database.bqFile
                      ) -> typing.Tuple[
                            typing.Union[
                              bigQuery_database.bqMainFile, bigQuery_database.bqOtherFile
                            ],
                            typing.List[bigQuery_database.bqHeaderFile]
                          ]:
    ## Do the same as inlineHeaders
    #  1. Parse file for #include
    #  2. Resolve include path
    #  3. Ping DB to get it
    #  4. Recurse over included file
    return contentfile, inlined_files

class RecursiveFetcher(GithubMiner):
  """GitHub API wrapper to pull from github a fresh corpus of OpenCL kernels"""

  class GithubRepoHandler():
    """Repo manager for recursive fetcher"""

    class GithubRepo():
      """Class representation of a single github Repo."""
      def __init__(self, **kwargs):
        # url of a repo is immutable.
        self.url = kwargs.get('url')
        if kwargs:
          self.update(**kwargs)
        return

      def update(self,
                 url          : str,
                 owner        : str,
                 name         : str,
                 fork         : int,
                 stars        : str,
                 contributors : int,
                 forks        : str,
                 created_at   : str,
                 updated_at   : str):

        if url != self.url:
          raise ValueError("Updated url of already existent repo does not match.")
        self.owner        = owner
        self.name         = name
        self.fork         = fork
        self.stars        = stars
        self.contributors = contributors
        self.forks        = forks
        self.created_at   = created_at
        self.updated_at   = updated_at
        return

    class GithubFile():
      """Class representation of a single github file."""
      def __init__(self, **kwargs):
        # url of a file is immutable
        self.url  = kwargs.get('url')
        self.size = 0
        if kwargs:
          self.update(**kwargs)

      def update(self,
                 url      : str,
                 contents : str,
                 path     : str,
                 repo_url : str,
                 sha      : str,
                 size     : int):

        if url != self.url:
          raise ValueError("Updated url of already existent file does not match.")

        self.contents   = contents
        self.path       = path
        self.repo_url   = repo_url
        self.sha        = sha
        if self.size != 0:
          current_size  = size - self.size
        else:
          current_size  = size
        self.size       = size
        return current_size

    def __init__(self, 
                 corpus_path: str,
                 corpus_size: int,
                 flush_limit: int,
                 ):

      ## Use this to read a json file with all current sha files
      ## And of course to append the json file every time you flush
      ## ..and to flush
      self.cache_path              = corpus_path
      self.stored_file_idx          = "record.json"

      self.updated_length           = 0

      self._scraped_repos           = {}
      self._stored_repos            = {}
      self._scraped_files           = {}

      self.repos_new_counter        = 0
      self.repos_modified_counter   = 0
      self.repos_unchanged_counter  = 0
      self.repos_stored_counter     = 0

      self.files_new_counter        = 0
      self.files_modified_counter   = 0
      self.files_unchanged_counter  = 0
      self.file_size_counter        = 0
      self.file_size_limit          = flush_limit

      self.collectHistory()
      self.is_finished              = False if (corpus_size // 1000) == -1 else (self.updated_length >= corpus_size)
      return

    def collectHistory(self) -> None:
      storage_file = os.path.join(self.cache_path, self.stored_file_idx)
      if os.path.isfile(storage_file):
        with open(storage_file, 'r') as f:
          try:
            data                = json.load(f)
            assert len(data)    == 2, "Wrong format of kernel history provided"
            self._stored_repos  = data[0]
            self.updated_length = data[1]['total_files']
          except json.JSONDecodeError:
            l.getLogger().warn("Problem encountered with reading kernel file record.")
      return

    def appendHistory(self) -> None:
      storage_file = os.path.join(self.cache_path, self.stored_file_idx)
      with open(storage_file, 'w') as f:
        json.dump(
          [self._stored_repos, 
           {'total_files': self.updated_length + copy.deepcopy(len(self._scraped_files))}],
          f, 
          indent = 2)
      return

    def is_repo_updated(self, url, updated_at) -> bool:
      if url in self._scraped_repos and self._scraped_repos[url].updated_at == updated_at:
        self.repos_unchanged_counter += 1
        return True
      elif url in self._stored_repos:# and self._stored_repos[url] == updated_at:
        self.repos_stored_counter    += 1
        return True
      return False
   
    def is_file_updated(self, url, sha) -> bool:
      if url in self._scraped_files and self._scraped_files[url].sha == sha:
        self.files_unchanged_counter += 1
        return True
      return False

    def update_file(self, **kwargs) -> bool:

      url = kwargs.get('url')
      if url in self._scraped_files:
        self.file_size_counter      += self._scraped_files[url].update(**kwargs)
        self.files_modified_counter += 1
      else:
        self._scraped_files[url]    =  RecursiveFetcher.GithubRepoHandler.GithubFile(**kwargs)
        self.files_new_counter      += 1
        self.file_size_counter      += kwargs.get('size')

      if self.file_size_counter >= self.file_size_limit:
        l.getLogger().warn("time to flush!")
        self.Flush()
        self.collectHistory()
        self.file_size_counter = 0

      return True

    def update_repo(self, **kwargs) -> bool:

      url = kwargs.get('url')
      if url in self._scraped_repos:
        self._scraped_repos[url].update(**kwargs)
        self.repos_modified_counter += 1
      else:
        self._scraped_repos[url]    =  RecursiveFetcher.GithubRepoHandler.GithubRepo(**kwargs)
        self.repos_new_counter      += 1
      return True

    def Flush(self) -> None:
      for idx, file in enumerate(self._scraped_files):
        with open(os.path.join(self.cache_path, "{}.cl".format(idx + self.updated_length)), 'w') as f:
          f.write(self._scraped_files[file].contents)
      for repo in self._scraped_repos:
        self._stored_repos[repo] = self._scraped_repos[repo].updated_at
      self.appendHistory()
      self._scraped_repos.clear()
      self._scraped_files.clear()
      self.file_size_counter  = 0
      return

    def print_counters(self) -> None:
      """
      Print analytics counters.
      """
      print('\r\033[Kfiles: new: ',  self.files_new_counter,
          ', modified: ',            self.files_modified_counter,
          ', mem_size: ',            self.file_size_counter, 'B',
          sep='', end='')


  def __init__(self,
               config: github_pb2.GithubMiner
               ):
    self.cache_path = pathlib.Path(config.path, must_exist = False).expanduser().resolve()
    self.cache_path.mkdir(exist_ok = True, parents = True)
    git_credentials = {
      'GITHUB_USERNAME'  : None,
      'GITHUB_PW'        : None,
    }
    l.getLogger().info("Github fetcher initialized: {}".format(self.cache_path))

    if not all(k in os.environ for k in git_credentials.keys()):
      l.getLogger().warn("Export github credentials as environment variables to speed up the process")

    for key in git_credentials:
      if key in os.environ:
        git_credentials[key] = os.environ[key]
      else:
        git_credentials[key] = input("{}: ".format(key))
        os.environ[key]      = git_credentials[key]

    self.username        = git_credentials['GITHUB_USERNAME']
    self.password        = git_credentials['GITHUB_PW']
    self.token           = config.recursive.access_token
    self.repo_handler    = RecursiveFetcher.GithubRepoHandler(
      self.cache_path, 
      config.recursive.corpus_size_K * 1000,
      config.recursive.flush_limit_K * 1000,
    )

    self.current_status  = ""
    self.errors_counter  = 0
    return

  def print_counters(self) -> None:
    self.repo_handler.print_counters()
    print('. errors: ', self.errors_counter,
          '. ',        self.current_status[0:80],
        sep='', end='')
    sys.stdout.flush()

  def fetch(self) -> None:
    """
    Download all of the OpenCL on GitHub (!)

    Shortcomings of this appraoch:
      * Only includes exclusively OpenCL files, no inline strings.
      * Occasionally (< 1%) can't find headers to include.

    """
    g = github.Github(self.username, self.password)
    handle_repo = partial(self.process_repo, g)

    # fetch the repositories to iterate over. Since opencl isn't
    # treated as a first-class language by GitHub, we can't use the
    # 'language=' keyword for queries, so instead we through a much
    # wider net and filter the results afterwards.
    query_terms = [
      'opencl',
      'cl',
      'khronos',
      'gpu',
      'gpgpu',
      'cuda',
      'amd',
      'nvidia',
      'heterogeneous'
    ]
    try:
      for query in query_terms:
        # forks are okay - we use checksums to ensure uniqueness in
        # final dataset
        repos = g.search_repositories(query + ' fork:true sort:stars')

        for repo in repos:
          if self.repo_handler.is_finished:
            self.print_counters()
            self.repo_handler.Flush()
            l.getLogger().info("Finished gathering Github kernels.")
            return

          repo_modified = handle_repo(repo)

          # do nothing unless the repo is new or modified
          if not repo_modified:
            continue

          handle_file = partial(self.process_file, g, repo)

          # iterate over the entire git tree of the repo's default
          # branch (usually 'master'). If a file ends with the .cl
          # extension, check to see if we already have it, else download
          # it
          try:
            branch = repo.default_branch
            tree_iterator = repo.get_git_tree(branch, recursive=True).tree
            for f in tree_iterator:
              try:
                handle_file(f)
              except UnicodeError:
                self.errors_counter += 1
                pass
              except Exception as e:
                raise e
          except github.GithubException:
            # do nothing in case of error (such as an empty repo)
            pass
    except KeyboardInterrupt:
      # Don't gather any more files
      pass
    except Exception as e:
      self.errors_counter += 1
      self.repo_handler.Flush()
      raise e

    self.print_counters()
    self.repo_handler.Flush()
    l.getLogger().info("Finished gathering Github kernels.")
    return

  def process_repo(self, g, repo) -> bool:
    """
    GitHub repository handler.

    Determines if a repository needs to be scraped. There are two cases for
    this:
      * The repository has not already been visited.
      * The repository has been modified since it was last visited.

    Parameters
    ----------
    g
      GitHub connection.
    repo
      Repository.
    Returns
    -------
    bool
      True if repository should be scraped, else False.
    """
    self.rate_limit(g)

    url                   = repo.url
    name                  = repo.name
    updated_at            = str(repo.updated_at)
    self.current_status   = name
    self.print_counters()

    if self.repo_handler.is_repo_updated(url, updated_at):
      # Timestamp of already scraped repo matches, so nothing to do.
      return False

    owner  = repo.owner.email
    fork   = 1 if repo.fork else 0
    stars  = repo.stargazers_count
    try:
      contributors = len([x for x in repo.get_contributors()])
    except github.GithubException:
      contributors = -1

    forks      = repo.forks
    created_at = repo.created_at

    self.repo_handler.update_repo(url          = url,       owner        = owner,
                                  name         = name,      fork         = fork,
                                  stars        = stars,     contributors = contributors,
                                  forks        = forks,     created_at   = created_at,
                                  updated_at   = updated_at )

    return True

  def process_file(self, g, repo, file) -> bool:
    """
    GitHub file handler.

    Parameters
    ----------
    g
      GitHub connection.
    repo
      Repository.
    file
      File.

    Returns
    -------
    bool
      True on success, else False.
    """
    # We're only interested in OpenCL files.
    if not (file.path.endswith('.cl') or file.path.endswith('.ocl')):
      return

    url = file.url
    sha = file.sha
    path = file.path
    self.current_status = repo.name + '/' + path
    self.print_counters()

    if self.repo_handler.is_file_updated(url, sha):
      # Do nothing unless checksums don't match
      return False

    repo_url = repo.url
    contents = self.download_file(repo, url)
    size     = file.size

    self.repo_handler.update_file(
      url = url, contents = contents, path = path,
      sha = sha, repo_url = repo_url, size = size
    )
    return True

  def download_file(self, repo, url: str, stack = []) -> str:
    """
    Fetch file from GitHub.

    Recursively downloads and inlines headers.

    Parameters
    ----------
    repo
      Repository.
    url : str
      Path.
    stack : List[str]
      URL stack.

    Returns
    -------
    str
      File contents.
    """
    # Recursion stack
    stack.append(url)

    response = json.loads(requests.get(
      url,
      headers={
        'Authorization': 'token ' + str(self.token)
      }
    ).content.decode('utf-8'))
    src = b64decode(response['content']).decode('utf-8')

    outlines = []
    for line in src.split('\n'):
      match = re.match(re.compile('\w*#include ["<](.*)[">]'), line)
      if match:
        include_name = match.group(1)

        # Try and resolve relative paths
        include_name = include_name.replace('../', '')

        branch = repo.default_branch
        tree_iterator = repo.get_git_tree(branch, recursive=True).tree
        include_url = ''
        for f in tree_iterator:
          if f.path.endswith(include_name):
            include_url = f.url
            break

        if include_url and include_url not in stack:
          include_src = self.download_file(repo, include_url, stack)
          outlines.append("// [FETCH] included: {}\n".format(line))
          outlines.append(include_src)
          outlines.append('// [FETCH] eof({})'.format(line))
        else:
          if not include_url:
            outlines.append('// [FETCH] didnt find: \n{}'.format(line))
          else:
            outlines.append('// [FETCH] skipped: {}'.format(line))
      else:
        outlines.append(line)

    return '\n'.join(outlines)

  def rate_limit(self, g) -> None:
    """
    Block on GitHub rate limit.

    Parameters
    ----------
    g
      GitHub connection.
    """
    remaining = g.get_rate_limit().rate.remaining
    while remaining < 100:
      time.sleep(1)
      self.current_status = 'WAITING ON RATE LIMIT: {}'.format(remaining)
      self.print_counters()
      remaining = g.get_rate_limit().rate.remaining

  def inline_fs_headers(self, path: str, stack: typing.List[str]) -> str:
    """
    Recursively inline headers in file.

    Parameters
    ----------
    path : str
      File.
    stack : typing.List[str]
      File stack.

    Returns
    -------
    str
      Inlined file.
    """
    stack.append(path)

    with io.open(path) as infile:
      src = infile.read()

    outlines = []
    for line in src.split('\n'):
      match = re.match(re.compile('\w*#include ["<](.*)[">]'), line)
      if match:
        include_name = match.group(1)

        # try and resolve relative paths
        include_name = include_name.replace('../', '')

        include_path = os.path.join(os.path.dirname(path), include_name)

        if os.path.exists(include_path) and include_path not in stack:
          include_src = inline_fs_headers(include_path, stack)
          outlines.append('// [FETCH] include: ' + include_path)
          outlines.append(include_src)
          outlines.append('// [FETCH] eof(' + include_path + ')')
        else:
          if include_path in stack:
            outlines.append('// [FETCH] ignored recursive include: ' +
                    include_path)
          else:
            outlines.append('// [FETCH] 404 not found: ' +
                    include_path)
      else:
        outlines.append(line)

    return '\n'.join(outlines)


  def process_cl_file(self, db_path: str, path: str) -> None:
    """
    Process OpenCL file.

    Parameters
    ----------
    db_path : str
      Path to output database.
    path : str
      Path to input file.

    Raises
    ------
    IOError
      In case of IO error.
    """
    db = dbutil.connect(db_path)
    c = db.cursor()

    l.getLogger().info("fetch {path}".format(path=os.path.abspath(path)))
    try:
      contents = inline_fs_headers(path, [])
    except IOError:
      raise IOError(
        "cannot read file '{path}'".format(path=os.path.abspath(path)))
    c.execute('INSERT OR IGNORE INTO ContentFiles VALUES(?,?)',
          (path, contents))

    db.commit()
    c.close()


  def fetch_files(self, db_path: str, paths: typing.List[str]=[]) -> None:
    """
    Fetch from a list of files.

    Parameters
    ----------
    db_path : str
      Output dataset.
    paths : typing.List[str]
      typing.List of file paths.
    """
    paths = fs.files_from_list(*paths)  # expand directories

    db = dbutil.connect(db_path)
    c = db.cursor()

    for path in paths:
      l.getLogger().info("fetch", path)
      try:
        contents = inline_fs_headers(path, [])
      except IOError:
        db.commit()
        raise IOError(
          "cannot read file '{path}'".format(path=os.path.abspath(path)))
      c.execute('INSERT OR IGNORE INTO ContentFiles VALUES(?,?)',
            (path, contents))

    db.commit()
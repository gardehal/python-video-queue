import os

from dotenv import load_dotenv
from grdUtil.InputUtil import joinAsString
from grdUtil.PrintUtil import asTable

load_dotenv()

class Settings():
    debug: bool = None
    localStoragePath: str = None
    logWatched: str = None
    downloadWebStreams: bool = None
    removeWatchedOnFetch: bool = None
    playedAlwaysWatched: bool = None
    watchedLogFilepath: str = None
    logDirPath: str = None
    browserBin: str = None
    fetchLimitSingleSource: int = None
    
    def __init__(self):
        self.debug = eval(os.environ.get("DEBUG"))
        self.localStoragePath = os.environ.get("LOCAL_STORAGE_PATH")
        self.logWatched = eval(os.environ.get("LOG_WATCHED"))
        self.downloadWebStreams = eval(os.environ.get("DOWNLOAD_WEB_STREAMS"))
        self.removeWatchedOnFetch = eval(os.environ.get("REMOVE_WATCHED_ON_FETCH"))
        self.playedAlwaysWatched = eval(os.environ.get("PLAYED_ALWAYS_WATCHED"))
        self.watchedLogFilepath = os.environ.get("WATCHED_LOG_FILEPATH")
        self.logDirPath = os.environ.get("LOG_DIR_PATH")
        self.browserBin = os.environ.get("BROWSER_BIN")
        self.fetchLimitSingleSource =  int(os.environ.get("FETCH_LIMIT_SINGLE_SOURCE"))
    
    def getAllSettingsAsString(self) -> str:
        """
        Get settings in .env settings/secrets file.

        Returns:
            str: a string of all settings/secrets in project from .env.
        """

        return joinAsString("DEBUG: ", self.debug,
               "\n", "LOCAL_STORAGE_PATH: ", self.localStoragePath,
               "\n", "LOG_WATCHED: ", self.logWatched,
               "\n", "DOWNLOAD_WEB_STREAMS: ", self.downloadWebStreams,
               "\n", "REMOVE_WATCHED_ON_FETCH: ", self.removeWatchedOnFetch,
               "\n", "PLAYED_ALWAYS_WATCHED: ", self.playedAlwaysWatched,
               "\n", "WATCHED_LOG_FILEPATH: ", self.watchedLogFilepath,
               "\n", "LOG_DIR_PATH: ", self.logDirPath,
               "\n", "BROWSER_BIN: ", self.browserBin,
               "\n", "FETCH_LIMIT_SINGLE_SOURCE: ", self.fetchLimitSingleSource)

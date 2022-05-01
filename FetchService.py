import os
import sys
from datetime import datetime
from typing import List

from dotenv import load_dotenv
from grdException.ArgumentException import ArgumentException
from grdUtil.BashColor import BashColor
from grdUtil.FileUtil import mkdir
from grdUtil.InputUtil import sanitize
from grdUtil.PrintUtil import printS
from pytube import Channel

from enums.StreamSourceType import StreamSourceType
from model.QueueStream import QueueStream
from model.StreamSource import StreamSource
from PlaylistService import PlaylistService
from QueueStreamService import QueueStreamService
from StreamSourceService import StreamSourceService

load_dotenv()
DEBUG = eval(os.environ.get("DEBUG"))
LOCAL_STORAGE_PATH = os.environ.get("LOCAL_STORAGE_PATH")

class FetchService():
    playlistService: PlaylistService = None
    queueStreamService: QueueStreamService = None
    streamSourceService: StreamSourceService = None

    def __init__(self):
        self.playlistService: PlaylistService = PlaylistService()
        self.queueStreamService: QueueStreamService = QueueStreamService()
        self.streamSourceService: StreamSourceService = StreamSourceService()

        mkdir(LOCAL_STORAGE_PATH)

    def fetch(self, playlistId: str, batchSize: int = 10, takeAfter: datetime = None, takeBefore: datetime = None, takeNewOnly: bool = False) -> int:
        """
        Fetch new videos from watched sources, adding them in chronological order.

        Args:
            batchSize (int): number of videos to check at a time, unrelated to max videos that will be read
            takeAfter (datetime): limit to take video after
            takeBefore (datetime): limit to take video before
            takeNewOnly (bool): only take streams marked as new. Disables takeAfter and takeBefore-checks. To use takeAfter and/or takeBefore, set this to False

        Returns:
            int: number of videos added
        """
        
        if(batchSize < 1):
            raise ArgumentException("fetch - batchSize was less than 1.")

        _playlist = self.playlistService.get(playlistId)
        if(_playlist == None):
            return 0

        _datetimeStarted = datetime.now()
        _newStreams = []
        for _sourceId in _playlist.streamSourceIds:
            _source = self.streamSourceService.get(_sourceId)
            
            if(_source == None):
                printS("StreamSource with ID ", _sourceId, " could not be found. Consider removing it using the purge commands.", color = BashColor.FAIL)
                continue
            
            if(not _source.enableFetch):
                continue

            _fetchedStreams = []
            _takeAfter = takeAfter if(not takeNewOnly) else _source.lastSuccessfulFetched
            
            if(_source.isWeb):
                if(_source.streamSourceTypeId == StreamSourceType.YOUTUBE.value):
                    _fetchedStreams = self.fetchYoutube(_source, batchSize, _takeAfter, takeBefore, takeNewOnly)
                else:
                    # TODO handle other sources
                    continue
            else:
                _fetchedStreams = self.fetchDirectory(_source, batchSize, _takeAfter, takeBefore, takeNewOnly)

            if(len(_fetchedStreams) > 0):
                _source.lastSuccessfulFetched = _datetimeStarted
            
            _source.lastFetchedIds = _fetchedStreams[1]
            _source.lastFetched = _datetimeStarted
            _updateSuccess = self.streamSourceService.update(_source)
            if(_updateSuccess):
                _newStreams += _fetchedStreams[0]
            else:
                printS("Could not update StreamSource \"", _source.name, "\" (ID: ", _source.id, "), streams could not be added: \n", _fetchedStreams, color = BashColor.WARNING)
                
            sys.stdout.flush()

        _updateResult = self.playlistService.addStreams(_playlist.id, _newStreams)
        if(len(_updateResult) > 0):
            return len(_newStreams)
        else:
            return 0

    def fetchYoutube(self, streamSource: StreamSource, batchSize: int = 10, takeAfter: datetime = None, takeBefore: datetime = None, takeNewOnly: bool = False) -> tuple[List[QueueStream], List[str]]:
        """
        Fetch videos from YouTube.

        Args:
            batchSize (int): number of videos to check at a time, unrelated to max videos that will be read
            takeAfter (datetime): limit to take video after
            takeBefore (datetime): limit to take video before
            takeNewOnly (bool): only take streams marked as new. Disables takeAfter and takeBefore-checks. To use takeAfter and/or takeBefore, set this to False

        Returns:
            tuple[List[QueueStream], str]: A tuple of List of QueueStream, and the last YouTube ID fetched 
        """
        
        if(streamSource == None):
            raise ArgumentException("fetchYoutube - streamSource was None.")

        _emptyReturn = ([], streamSource.lastFetchedIds)
        _channel = Channel(streamSource.uri)

        if(_channel == None or _channel.channel_name == None):
            printS("Channel \"", streamSource.name, "\" (URL: ", streamSource.uri, ") could not be found or is not valid. Please remove it and add it back.", color = BashColor.FAIL)
            return _emptyReturn

        printS("Fetching videos from ", _channel.channel_name, "...")
        sys.stdout.flush()
        if(len(_channel.video_urls) < 1):
            printS("Channel \"", _channel.channel_name, "\" has no videos.", color = BashColor.WARNING)
            return _emptyReturn

        _newStreams = []
        _streams = list(_channel.videos)
        _lastStreamId = _streams[0].video_id
        if(takeNewOnly and takeAfter == None and _lastStreamId in streamSource.lastFetchedIds):
            printS("DEBUG: fetchYoutube - last video fetched: \"", sanitize(_streams[0].title), "\", YouTube ID \"", _lastStreamId, "\"", color = BashColor.WARNING)
            printS("DEBUG: fetchYoutube - return due to takeNewOnly and takeAfter == None and _lastStreamId in streamSource.lastFetchedIds", color = BashColor.WARNING)
            return _emptyReturn
            
        for i, _stream in enumerate(_streams):
            if(takeNewOnly and _stream.video_id in streamSource.lastFetchedIds):
                printS("DEBUG: fetchYoutube - name \"", sanitize(_stream.title), "\", YouTube ID \"", _stream.video_id, "\"", color = BashColor.WARNING)
                printS("DEBUG: fetchYoutube - break due to takeNewOnly and _stream.video_id in streamSource.lastFetchedIds", color = BashColor.WARNING)
                break
            elif(not takeNewOnly and takeAfter != None and _stream.publish_date < takeAfter):
                printS("DEBUG: fetchYoutube - break due to not takeNewOnly and takeAfter != None and _stream.publish_date < takeAfter", color = BashColor.WARNING)
                break
            elif(not takeNewOnly and takeBefore != None and _stream.publish_date > takeBefore):
                printS("DEBUG: fetchYoutube - continue due to not takeNewOnly and takeBefore != None and _stream.publish_date > takeBefore", color = BashColor.WARNING)
                continue
            elif(i > batchSize):
                printS("DEBUG: fetchYoutube - break due to i > batchSize", color = BashColor.WARNING)
                break
            
            _sanitizedTitle = sanitize(_stream.title)
            printS("\tAdding \"", _sanitizedTitle, "\"...")
            _stream = QueueStream(name = _sanitizedTitle, 
                                           uri = _stream.watch_url, 
                                           isWeb = True,
                                           streamSourceId = streamSource.id,
                                           watched = None,
                                           backgroundContent = streamSource.backgroundContent,
                                           added = datetime.now())
            _newStreams.append(_stream)
            
        streamSource.lastFetchedIds.append(_lastStreamId)
        if(len(streamSource.lastFetchedIds) > batchSize):
            streamSource.lastFetchedIds.pop(0)
        
        return (_newStreams, streamSource.lastFetchedIds)

    def fetchDirectory(self, streamSource: StreamSource, batchSize: int = 10, takeAfter: datetime = None, takeBefore: datetime = None, takeNewOnly: bool = False) -> tuple[List[QueueStream], str]:
        """
        Fetch streams from a local directory.

        Args:
            batchSize (int): number of videos to check at a time, unrelated to max videos that will be read
            takeAfter (datetime): limit to take video after
            takeBefore (datetime): limit to take video before
            takeNewOnly (bool): only take streams marked as new. Disables takeAfter and takeBefore-checks. To use takeAfter and/or takeBefore, set this to False

        Returns:
            tuple[List[QueueStream], str]: A tuple of List of QueueStream, and the last filename fetched 
        """
        
        if(streamSource == None):
            raise ValueError("fetchDirectory - streamSource was None")

        _emptyReturn = ([], streamSource.lastFetchedIds)
        return _emptyReturn
    
    def resetPlaylistFetch(self, playlistIds: List[str]) -> int:
        """
        Reset the fetch-status for sources of a playlist and deletes all streams.

        Args:
            playlistIds (List[str]): list of playlistIds 
            
        Returns:
            int: number of playlists reset
        """
        
        _result = 0
        for playlistId in playlistIds:            
            _playlist = self.playlistService.get(playlistId)
            _deleteUpdateResult = True
            
            for queueStreamId in _playlist.streamIds:
                _deleteStreamResult = self.queueStreamService.delete(queueStreamId)
                _deleteUpdateResult = _deleteUpdateResult and _deleteStreamResult != None
            
            _playlist.streamIds = []
            _updateplaylistResult = self.playlistService.update(_playlist)
            _deleteUpdateResult = _deleteUpdateResult and _updateplaylistResult != None
            
            for streamSourceId in _playlist.streamSourceIds:
                _streamSource = self.streamSourceService.get(streamSourceId)
                _streamSource.lastFetched = None
                _updateStreamResult = self.streamSourceService.update(_streamSource)
                _deleteUpdateResult = _deleteUpdateResult and _updateStreamResult != None
            
            if(_deleteUpdateResult):
                _result += 1
                
        return _result

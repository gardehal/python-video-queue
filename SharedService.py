import os
import re
from typing import List

import mechanize
from dotenv import load_dotenv
from grdUtil.BashColor import BashColor
from grdUtil.InputUtil import sanitize
from grdUtil.PrintUtil import printS
from grdUtil.StaticUtil import StaticUtil
from pytube import YouTube

from enums.StreamSourceType import StreamSourceType, StreamSourceTypeUtil
from model.Playlist import Playlist
from model.QueueStream import QueueStream
from model.StreamSource import StreamSource
from PlaylistService import PlaylistService
from QueueStreamService import QueueStreamService
from StreamSourceService import StreamSourceService

load_dotenv()
DEBUG = eval(os.environ.get("DEBUG"))
LOCAL_STORAGE_PATH = os.environ.get("LOCAL_STORAGE_PATH")
LOG_WATCHED = eval(os.environ.get("LOG_WATCHED"))
DOWNLOAD_WEB_STREAMS = eval(os.environ.get("DOWNLOAD_WEB_STREAMS"))
REMOVE_WATCHED_ON_FETCH = eval(os.environ.get("REMOVE_WATCHED_ON_FETCH"))
PLAYED_ALWAYS_WATCHED = eval(os.environ.get("PLAYED_ALWAYS_WATCHED"))
WATCHED_LOG_FILEPATH = os.environ.get("WATCHED_LOG_FILEPATH")
BROWSER_BIN = os.environ.get("BROWSER_BIN")

class SharedService():
    storagePath: str = LOCAL_STORAGE_PATH
    playlistService: PlaylistService = None
    queueStreamService: QueueStreamService = None
    streamSourceService: StreamSourceService = None

    def __init__(self):
        self.playlistService: PlaylistService = PlaylistService()
        self.queueStreamService: QueueStreamService = QueueStreamService()
        self.streamSourceService: StreamSourceService = StreamSourceService()

    def getPageTitle(self, url: str) -> str:
        """
        Get page title from the URL url, using mechanize or PyTube.

        Args:
            url (str): URL to page to get title from.

        Returns:
            str: Title of page.
        """
        
        isYouTubeChannel = "user" in url or "channel" in url  
        if(StreamSourceTypeUtil.strToStreamSourceType(url) == StreamSourceType.YOUTUBE and not isYouTubeChannel):
            printS("DEBUG: getPageTitle - Getting title from pytube.", color = BashColor.WARNING, doPrint = DEBUG)
            yt = YouTube(url)
            title = yt.title
        else:
            printS("DEBUG: getPageTitle - Getting title from mechanize.", color = BashColor.WARNING, doPrint = DEBUG)
            br = mechanize.Browser()
            br.open(url)
            title = br.title()
            br.close()

        return sanitize(title).strip()

    def preparePrune(self, playlistId: str, includeSoftDeleted: bool = False) -> dict[list[Playlist], list[QueueStream]]:
        """
        Prepare a prune to permanently remove all soft-deleted entities, getting data for doPrune.
        
        Args:
            playlistId (str): ID of playlist to prune.
            includeSoftDeleted (bool, optional): Should include soft-deleted entities. Defaults to False.
            
        Returns:
            dict[list[Playlist], list[QueueStream]]: Entities to remove.
        """
        
        dataEmpty = { "Playlist": [], "QueueStream": []}
        data = dataEmpty

        playlist = self.playlistService.get(playlistId, includeSoftDeleted)
        if(playlist == None or playlist.playWatchedStreams):
            return dataEmpty
        
        data["Playlist"].append(playlist)
        for id in playlist.streamIds:
            stream = self.queueStreamService.get(id, includeSoftDeleted)
            if(stream != None and stream.watched != None):
                data["QueueStream"].append(stream)
        
        return data
    
    def doPrune(self, data: dict[list[Playlist], list[QueueStream]], permanentlyDelete: bool = False) -> bool:
        """
        Prune (permanently remove/soft delete) watched QueueStreams from Playlists given as data.
        
        Args:
            dict[list[Playlist], list[QueueStream]]): Data to remove.
            permanentlyDelete (bool): Should entities be permanently deleted.
            
        Returns:
            bool: Result.
        """
        
        # for stream in deletedData["QueueStream"]:
        #     if(permanentlyDelete):
        #         self.queueStreamService.remove(stream.id, includeSoftDeleted)
        #     else:
        #         self.queueStreamService.delete(stream.id)
                
        #     playlist.streamIds.remove(stream.id)
        
        # updateResult = self.playlistService.update(playlist)
        # if(updateResult != None):
        #     return deletedData
        # else:
        #     return deletedDataEmpty
            
        return True
    
    def preparePurge(self) -> dict[list[QueueStream], list[StreamSource], list[Playlist]]:
        """
        Prepare a purge to permanently remove all soft-deleted entities, getting data for doPurge.
            
        Returns:
            dict[list[QueueStream], list[StreamSource], list[Playlist]]: Entities to remove.
        """
        
        dataEmpty = {"QueueStream": [], "StreamSource": [], "Playlist": []}
        data = dataEmpty
        
        allQ = self.queueStreamService.getAll(includeSoftDeleted = True)
        data["QueueStream"] = [_ for _ in allQ if _.deleted != None]
        allS = self.streamSourceService.getAll(includeSoftDeleted = True)
        data["StreamSource"] = [_ for _ in allS if _.deleted != None]
        allP = self.playlistService.getAll(includeSoftDeleted = True)
        data["Playlist"] = [_ for _ in allP if _.deleted != None]
        
        return data
    
    def doPurge(self, data: dict[list[QueueStream], list[StreamSource], list[Playlist]]) -> bool:
        """
        Purge (permanently remove) all soft-deleted entities given as data.
            
        Args:
            data (dict[list[QueueStream], list[StreamSource], list[Playlist]]): Data to remove.
            
        Returns:
            bool: Result.
        """
        
        for _ in data["QueueStream"]:
            self.queueStreamService.remove(_.id, True)
        for _ in data["StreamSource"]:
            self.streamSourceService.remove(_.id, True)
        for _ in data["Playlist"]:
            self.playlistService.remove(_.id, True)
            
        return True
    
    def preparePurgePlaylists(self, includeSoftDeleted: bool = False, permanentlyDelete: bool = False) -> dict[list[QueueStream], list[StreamSource], list[Playlist]]:
        """
        Prepare a purge to delete/permanently remove QueueStreams and StreamSources from DB, while removing IDs with no entity from Playlists, getting data for doPurgePlaylists.
        
        Args:
            includeSoftDeleted (bool): Should soft-deleted entities be deleted.
            permanentlyDelete (bool): Should entities be permanently deleted.
            
        Returns:
            dict[list[QueueStream], list[StreamSource], list[Playlist]]: Entities to remove.
        """
        
        dataEmpty = {"QueueStream": [], "StreamSource": [], "Playlist": []}
        data = dataEmpty
        playlists = self.playlistService.getAll(includeSoftDeleted)
        qIds = self.queueStreamService.getAllIds(includeSoftDeleted)
        sIds = self.streamSourceService.getAllIds(includeSoftDeleted)
        
        # Get all playlists
        # get all qs and ss ids from playlists
        # get all IDs of qs and ss
        # remove overlapping playlist ids with all ids, the remaining are unlinked qs and ss
        
        # for each id in unlinked entities, if id in playlist, add playlist to list
        
        allPlaylistQueueStreamIds = []
        allPlaylistStreamStreamIds = []
        for playlist in playlists:
            allPlaylistQueueStreamIds.extend(playlist.streamIds)
            allPlaylistStreamStreamIds.extend(playlist.streamSourceIds)
        
        unlinkedPlaylistQueueStreamIds = [_ for _ in qIds if(_ not in allPlaylistQueueStreamIds)]
        unlinkedPlaylistStreamStreamIds = [_ for _ in sIds if(_ not in allPlaylistStreamStreamIds)]
        
        # Find unlinked QueueStreams and StreamSources (not found in any Playlists)
        for id in unlinkedPlaylistQueueStreamIds:
            if(not id in allPlaylistQueueStreamIds):
                entity = self.queueStreamService.get(id, includeSoftDeleted)
                data["QueueStream"].append(entity)
        for id in unlinkedPlaylistStreamStreamIds:
            if(not id in allPlaylistStreamStreamIds):
                entity = self.streamSourceService.get(id, includeSoftDeleted)
                data["StreamSource"].append(entity)
        
        # Find IDs in Playlists with no corresponding entity
        for playlist in playlists:
            for id in playlist.streamIds:
                if(not self.queueStreamService.exists(id)):
                    data["Playlist"].append(playlist)
                    break
                
            for id in playlist.streamSourceIds:
                if(not self.streamSourceService.exists(id)):
                    data["Playlist"].append(playlist)
                    break
                
        return data
    
    def doPurgePlaylists(self, data: dict[list[Playlist]]) -> bool:
        """
        Purge Playlists given as data for dangling IDs.
            
        Args:
            data (dict[list[Playlist]]): Data to remove where Playlist-list is Playlists to update, and str-list are IDs to remove from any field in Playlists.
            
        Returns:
            bool: Result.
        """
        
        for playlist in data["Playlist"]:
            updatedStreamIds = []
            updatedStreamSourceService = []
            
            for id in playlist.streamIds:
                if(self.queueStreamService.exists(id)):
                    updatedStreamIds.append(id)
                    
            for id in playlist.streamSourceIds:
                if(self.streamSourceService.exists(id)):
                    updatedStreamSourceService.append(id)
                
            playlist.streamIds = updatedStreamIds
            playlist.streamSourceIds = updatedStreamSourceService
            
            self.playlistService.update(playlist)
            
        return True
        
    def purgePlaylists(self, includeSoftDeleted: bool = False, permanentlyDelete: bool = False) -> dict[List[QueueStream], List[StreamSource], List[str], List[str]]:
        """
        Purges the dangling IDs from Playlists, and purge unlinked StreamSources and QueueStreams.

        Args:
            includeSoftDeleted (bool): Should soft-deleted entities be deleted.
            permanentlyDelete (bool): Should entities be permanently deleted.
            
        Returns:
            dict[List[QueueStream], List[StreamSource], List[str], List[str]]: StreamSources removed, QueueStreams removed, QueueStreamId removed from playlists, and StreamSourceId removed.
        """
        
        deletedDataEmpty = {"QueueStream": [], "StreamSource": [], "QueueStreamId": [], "StreamSourceId": []}
        deletedData = deletedDataEmpty
        playlists = self.playlistService.getAll(includeSoftDeleted)
        streamsIds = self.queueStreamService.getAllIds(includeSoftDeleted)
        sourcesIds = self.streamSourceService.getAllIds(includeSoftDeleted)
        
        playlistStreams = []
        playlistSources = []
        updatedPlaylists = []
        for playlist in playlists:
            playlistStreams.extend(playlist.streamIds)
            playlistSources.extend(playlist.streamSourceIds)
        
        for id in streamsIds:
            if(not id in playlistStreams):
                entity = self.queueStreamService.get(id, includeSoftDeleted)
                deletedData["QueueStream"].append(entity)
        for id in sourcesIds:
            if(not id in playlistSources):
                entity = self.streamSourceService.get(id, includeSoftDeleted)
                deletedData["StreamSource"].append(entity)
                
        for playlist in playlists:
            streamIdsToRemove = []
            sourceIdsToRemove = []
            
            for id in playlist.streamIds:
                stream = self.queueStreamService.get(id, includeSoftDeleted)
                if(stream == None):
                    streamIdsToRemove.append(id)
                    
            for id in playlist.streamSourceIds:
                source = self.streamSourceService.get(id, includeSoftDeleted)
                if(source == None):
                    sourceIdsToRemove.append(id)
                    
            if(len(streamIdsToRemove) > 0 or len(sourceIdsToRemove) > 0):
                for id in streamIdsToRemove:
                    playlist.streamIds.remove(id)
                for id in sourceIdsToRemove:
                    playlist.streamSourceIds.remove(id)
                
                updatedPlaylists.append(playlist)
        
        printS("\nPurge summary, the following data will be", (" PERMANENTLY REMOVED" if permanentlyDelete else " DELETED"), ":", color = BashColor.WARNING)
        
        printS("\nQueueStream(s)", color = BashColor.BOLD)
        printS("No QueueStream(s) will be", (" permanently" if permanentlyDelete else ""), " removed", doPrint = len(deletedData["QueueStream"]) == 0)
        for _ in deletedData["QueueStream"]:
            print(_.id + " - " + _.name)
            
        printS("\nStreamSource(s)", color = BashColor.BOLD)
        printS("No StreamSource(s) will be removed", doPrint = len(deletedData["StreamSource"]) == 0)
        for _ in deletedData["StreamSource"]:
            print(_.id + " - " + _.name)
            
        printS("\nDangling QueueStream ID(s)", color = BashColor.BOLD)
        printS("No ID(s) will be removed", doPrint = len(deletedData["QueueStreamId"]) == 0)
        for _ in deletedData["QueueStreamId"]:
            print(_.id + " - " + _.name)
            
        printS("\nDangling StreamSource ID(s)", color = BashColor.BOLD)
        printS("No ID(s) will be removed", doPrint = len(deletedData["StreamSourceId"]) == 0)
        for _ in deletedData["StreamSourceId"]:
            print(_.id + " - " + _.name)
        
        printS("\nRemoving ", len(deletedData["QueueStream"]), " unlinked QueueStream(s), ", len(deletedData["StreamSource"]), " unlinked StreamSource(s).")
        printS("Removing ", len(deletedData["QueueStreamId"]), " dangling QueueStream ID(s), ", len(deletedData["StreamSourceId"]), " dangling StreamSource ID(s).")
        printS("Do you want to", (" PERMANENTLY REMOVE" if permanentlyDelete else " DELETE"), " this data?", color = BashColor.WARNING)
        inputArgs = input("(y/n):")
        if(inputArgs not in StaticUtil.affirmative):
            printS("Purge aborted by user.", color = BashColor.WARNING)
            return deletedDataEmpty
            
        if(len(deletedData["QueueStream"]) == 0 and len(deletedData["StreamSource"]) == 0 and len(deletedData["QueueStreamId"]) == 0 and len(deletedData["StreamSourceId"]) == 0):
            printS("No data was available.", color = BashColor.WARNING)
            return deletedDataEmpty
            
        for _ in deletedData["QueueStream"]:
            if(permanentlyDelete):
                self.queueStreamService.remove(_.id, includeSoftDeleted)
            else:
                self.queueStreamService.delete(_.id)
                
        for _ in deletedData["StreamSource"]:
            if(permanentlyDelete):
                self.streamSourceService.remove(_.id, includeSoftDeleted)
            else:
                self.streamSourceService.delete(_.id)
        
        for playlist in updatedPlaylists:
            self.playlistService.update(playlist)
            
        return deletedData
    
    def search(self, searchTerm: str, includeSoftDeleted: bool = False) -> dict[List[QueueStream], List[StreamSource], List[Playlist]]:
        """
        Search names and URIs for Regex-term searchTerm and returns a dict with results.

        Args:
            searchTerm (str): Regex-enabled term to search for.
            includeSoftDeleted (bool, optional): Should include soft deleted entities. Defaults to False.

        Returns:
            dict[List[QueueStream], List[StreamSource], List[Playlist]]: Entities that matched the searchTerm.
        """
        
        dataEmpty = {"QueueStream": [], "StreamSource": [], "Playlist": []}
        data = dataEmpty
        
        queueStreams = self.queueStreamService.getAll(includeSoftDeleted)
        streamSources = self.streamSourceService.getAll(includeSoftDeleted)
        playlists = self.playlistService.getAll(includeSoftDeleted)
        
        for entity in queueStreams:
            if(self.searchFields(searchTerm, entity.name, entity.uri) > 0):
                data["QueueStream"].append(entity)
        for entity in streamSources:
            if(self.searchFields(searchTerm, entity.name, entity.uri) > 0):
                data["StreamSource"].append(entity)
        for entity in playlists:
            if(self.searchFields(searchTerm, entity.name) > 0):
                data["Playlist"].append(entity)
        
        found = len(data["QueueStream"]) > 0 or len(data["StreamSource"]) > 0 or len(data["Playlist"]) > 0
        printS("DEBUG: search - no results", color = BashColor.WARNING, doPrint = DEBUG and not found)
        
        return data 
    
    def searchFields(self, searchTerm: str, *fields) -> int:
        """
        Searchs *fields for Regex-enabled searchTerm.

        Args:
            searchTerm (str): Regex-enabled term to search for.
            fields (any): Fields to search.

        Returns:
            int: int of field first found in, 0 = not found, 1 = first field-argument etc.
        """
        
        for i, field in enumerate(fields):
            if(re.search(searchTerm, field, re.IGNORECASE)):
                return i + 1
        
        return 0
    
    def getAllSoftDeleted(self) -> dict[List[QueueStream], List[StreamSource], List[Playlist]]:
        """
        Returns a dict with lists of all soft deleted entities.

        Returns:
            dict[List[QueueStream], List[StreamSource], List[Playlist]]: Entities that matched the searchTerm.
        """
        
        dataEmpty = {"QueueStream": [], "StreamSource": [], "Playlist": []}
        data = dataEmpty
        
        queueStreams = self.queueStreamService.getAll(includeSoftDeleted = True)
        streamSources = self.streamSourceService.getAll(includeSoftDeleted = True)
        playlists = self.playlistService.getAll(includeSoftDeleted = True)
        
        for entity in queueStreams:
            if(entity.deleted != None):
                data["QueueStream"].append(entity)
        for entity in streamSources:
            if(entity.deleted != None):
                data["StreamSource"].append(entity)
        for entity in playlists:
            if(entity.deleted != None):
                data["Playlist"].append(entity)
        
        return data

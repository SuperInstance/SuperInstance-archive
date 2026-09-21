"""
Audio Ambiance Service

Manages background music, ambient sounds, and audio atmosphere for D&D sessions
with support for playlists, crossfading, and synchronized playback across clients.
"""

import asyncio
import json
import math
import os
import uuid
import random
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from pathlib import Path
import threading
from enum import Enum

import pygame
import mutagen
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.flac import FLAC

from ..models.base import BaseSessionModel
from ..models.content import AudioTrack, Playlist, AmbianceScene, AudioCue
from ..models.session import SessionSchema
from ..config import AUDIO_CONFIG


class PlaybackState(str, Enum):
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    CROSSFADING = "crossfading"


class AudioPlayer:
    """Core audio player with crossfading capabilities"""
    
    def __init__(self):
        pygame.mixer.pre_init(
            frequency=AUDIO_CONFIG["sample_rate"],
            size=-16,
            channels=2,
            buffer=512
        )
        pygame.mixer.init()
        
        self.current_track: Optional[AudioTrack] = None
        self.next_track: Optional[AudioTrack] = None
        self.state = PlaybackState.STOPPED
        self.volume = 1.0
        self.crossfade_duration = 3.0
        
        # Multiple channel support for layered audio
        self.channels = {
            'music': pygame.mixer.Channel(0),
            'ambiance': pygame.mixer.Channel(1),
            'sfx': pygame.mixer.Channel(2)
        }
        
        self.channel_volumes = {
            'music': 0.7,
            'ambiance': 0.5,
            'sfx': 0.8
        }
        
        self.loaded_sounds: Dict[str, pygame.mixer.Sound] = {}
        self._crossfade_task: Optional[asyncio.Task] = None
    
    async def load_track(self, track: AudioTrack) -> bool:
        """Load an audio track"""
        try:
            if track.id not in self.loaded_sounds:
                if not os.path.exists(track.file_path):
                    return False
                
                sound = pygame.mixer.Sound(track.file_path)
                self.loaded_sounds[track.id] = sound
            
            return True
        except Exception as e:
            print(f"Error loading track {track.file_path}: {e}")
            return False
    
    async def play_track(self, track: AudioTrack, channel: str = 'music',
                        fade_in: float = 0.0, loop: bool = False) -> bool:
        """Play a track on specified channel"""
        if not await self.load_track(track):
            return False
        
        try:
            sound = self.loaded_sounds[track.id]
            channel_obj = self.channels.get(channel)
            
            if channel_obj:
                loops = -1 if loop else 0
                
                if fade_in > 0:
                    channel_obj.play(sound, loops=loops, fade_ms=int(fade_in * 1000))
                else:
                    channel_obj.play(sound, loops=loops)
                
                # Set channel volume
                channel_obj.set_volume(self.channel_volumes[channel] * self.volume)
                
                if channel == 'music':
                    self.current_track = track
                    self.state = PlaybackState.PLAYING
                
                return True
        
        except Exception as e:
            print(f"Error playing track: {e}")
            return False
        
        return False
    
    async def crossfade_to(self, new_track: AudioTrack, 
                          duration: float = 3.0) -> bool:
        """Crossfade from current track to new track"""
        if self.state == PlaybackState.CROSSFADING:
            return False
        
        if not await self.load_track(new_track):
            return False
        
        self.state = PlaybackState.CROSSFADING
        self.next_track = new_track
        self.crossfade_duration = duration
        
        # Cancel existing crossfade
        if self._crossfade_task and not self._crossfade_task.done():
            self._crossfade_task.cancel()
        
        self._crossfade_task = asyncio.create_task(self._perform_crossfade())
        return True
    
    async def _perform_crossfade(self):
        """Internal crossfade implementation"""
        try:
            steps = 50
            fade_step = self.crossfade_duration / steps
            
            # Start new track at volume 0
            new_sound = self.loaded_sounds[self.next_track.id]
            new_channel = pygame.mixer.Channel(3)  # Temporary channel for crossfade
            new_channel.play(new_sound, loops=-1)
            new_channel.set_volume(0)
            
            # Fade out current, fade in new
            for i in range(steps + 1):
                progress = i / steps
                
                # Current track fade out
                current_vol = (1 - progress) * self.channel_volumes['music'] * self.volume
                self.channels['music'].set_volume(current_vol)
                
                # New track fade in
                new_vol = progress * self.channel_volumes['music'] * self.volume
                new_channel.set_volume(new_vol)
                
                await asyncio.sleep(fade_step)
            
            # Stop old track and switch channels
            self.channels['music'].stop()
            self.channels['music'].play(new_sound, loops=-1)
            self.channels['music'].set_volume(self.channel_volumes['music'] * self.volume)
            new_channel.stop()
            
            self.current_track = self.next_track
            self.next_track = None
            self.state = PlaybackState.PLAYING
        
        except asyncio.CancelledError:
            # Cleanup on cancellation
            if hasattr(self, 'new_channel'):
                new_channel.stop()
            self.state = PlaybackState.PLAYING
    
    async def stop_channel(self, channel: str, fade_out: float = 0.0):
        """Stop playback on a specific channel"""
        channel_obj = self.channels.get(channel)
        if channel_obj and channel_obj.get_busy():
            if fade_out > 0:
                channel_obj.fadeout(int(fade_out * 1000))
            else:
                channel_obj.stop()
            
            if channel == 'music':
                self.current_track = None
                self.state = PlaybackState.STOPPED
    
    async def set_volume(self, volume: float, channel: str = None):
        """Set volume for specific channel or all channels"""
        self.volume = max(0.0, min(1.0, volume))
        
        if channel:
            if channel in self.channels:
                self.channels[channel].set_volume(
                    self.channel_volumes[channel] * self.volume
                )
        else:
            for ch_name, ch_obj in self.channels.items():
                ch_obj.set_volume(self.channel_volumes[ch_name] * self.volume)
    
    def get_playback_position(self) -> float:
        """Get current playback position in seconds"""
        # This is a simplified implementation
        # Real implementation would track position more accurately
        return 0.0
    
    def cleanup(self):
        """Clean up resources"""
        if self._crossfade_task and not self._crossfade_task.done():
            self._crossfade_task.cancel()
        
        for channel in self.channels.values():
            channel.stop()
        
        pygame.mixer.quit()


class PlaylistManager:
    """Manages playlists and track sequencing"""
    
    def __init__(self):
        self.playlists: Dict[str, Playlist] = {}
        self.current_playlist: Optional[Playlist] = None
        self.current_index = 0
        self.shuffle_order: List[int] = []
        self.repeat_mode = "none"  # none, single, playlist
    
    async def create_playlist(self, name: str, tracks: List[AudioTrack],
                             created_by: str, tags: List[str] = None) -> str:
        """Create a new playlist"""
        playlist = Playlist(
            id=str(uuid.uuid4()),
            name=name,
            tracks=tracks,
            created_by=created_by,
            created_at=datetime.utcnow(),
            tags=tags or []
        )
        
        self.playlists[playlist.id] = playlist
        return playlist.id
    
    async def load_playlist(self, playlist_id: str) -> bool:
        """Load a playlist for playback"""
        if playlist_id not in self.playlists:
            return False
        
        self.current_playlist = self.playlists[playlist_id]
        self.current_index = 0
        self._generate_shuffle_order()
        return True
    
    def _generate_shuffle_order(self):
        """Generate randomized play order"""
        if not self.current_playlist:
            return
        
        self.shuffle_order = list(range(len(self.current_playlist.tracks)))
        random.shuffle(self.shuffle_order)
    
    async def get_next_track(self, shuffle: bool = False) -> Optional[AudioTrack]:
        """Get the next track in the playlist"""
        if not self.current_playlist or not self.current_playlist.tracks:
            return None
        
        if shuffle:
            if not self.shuffle_order:
                self._generate_shuffle_order()
            
            if self.current_index >= len(self.shuffle_order):
                if self.repeat_mode == "playlist":
                    self.current_index = 0
                    self._generate_shuffle_order()  # Re-shuffle
                else:
                    return None
            
            track_index = self.shuffle_order[self.current_index]
        else:
            track_index = self.current_index
            
            if track_index >= len(self.current_playlist.tracks):
                if self.repeat_mode == "playlist":
                    track_index = 0
                    self.current_index = 0
                else:
                    return None
        
        track = self.current_playlist.tracks[track_index]
        
        if self.repeat_mode != "single":
            self.current_index += 1
        
        return track
    
    async def get_previous_track(self) -> Optional[AudioTrack]:
        """Get the previous track in the playlist"""
        if not self.current_playlist or not self.current_playlist.tracks:
            return None
        
        self.current_index = max(0, self.current_index - 2)  # -2 because get_next increments
        return await self.get_next_track()
    
    async def jump_to_track(self, track_index: int) -> Optional[AudioTrack]:
        """Jump to a specific track in the playlist"""
        if (not self.current_playlist or 
            track_index < 0 or 
            track_index >= len(self.current_playlist.tracks)):
            return None
        
        self.current_index = track_index
        return self.current_playlist.tracks[track_index]


class AmbianceManager:
    """Manages ambient scenes and layered audio"""
    
    def __init__(self):
        self.scenes: Dict[str, AmbianceScene] = {}
        self.active_scene: Optional[AmbianceScene] = None
        self.active_layers: Dict[str, AudioTrack] = {}
    
    async def create_scene(self, name: str, description: str,
                          layers: List[AudioTrack], created_by: str,
                          tags: List[str] = None) -> str:
        """Create a new ambiance scene"""
        scene = AmbianceScene(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            audio_layers=layers,
            created_by=created_by,
            created_at=datetime.utcnow(),
            tags=tags or []
        )
        
        self.scenes[scene.id] = scene
        return scene.id
    
    async def activate_scene(self, scene_id: str, player: AudioPlayer,
                           fade_duration: float = 2.0) -> bool:
        """Activate an ambiance scene"""
        if scene_id not in self.scenes:
            return False
        
        scene = self.scenes[scene_id]
        
        # Stop current ambiance
        await player.stop_channel('ambiance', fade_duration / 2)
        
        # Wait for fade out
        await asyncio.sleep(fade_duration / 2)
        
        # Start new scene layers
        for i, layer in enumerate(scene.audio_layers):
            # Stagger layer starts slightly for more natural feel
            if i > 0:
                await asyncio.sleep(0.1)
            
            await player.play_track(
                layer, 
                channel='ambiance',
                fade_in=fade_duration / 2,
                loop=True
            )
        
        self.active_scene = scene
        return True
    
    async def add_layer(self, track: AudioTrack, layer_name: str,
                       player: AudioPlayer) -> bool:
        """Add a new audio layer to the current scene"""
        if layer_name in self.active_layers:
            return False
        
        success = await player.play_track(
            track, channel='ambiance', fade_in=1.0, loop=True
        )
        
        if success:
            self.active_layers[layer_name] = track
        
        return success
    
    async def remove_layer(self, layer_name: str, player: AudioPlayer) -> bool:
        """Remove an audio layer from the current scene"""
        if layer_name not in self.active_layers:
            return False
        
        await player.stop_channel('ambiance', fade_out=1.0)
        del self.active_layers[layer_name]
        return True


class AudioCueManager:
    """Manages audio cues and triggers"""
    
    def __init__(self):
        self.cues: Dict[str, AudioCue] = {}
        self.scheduled_cues: List[Tuple[datetime, AudioCue]] = []
    
    async def create_cue(self, name: str, track: AudioTrack,
                        trigger_condition: str, created_by: str,
                        volume: float = 1.0, delay_seconds: float = 0.0) -> str:
        """Create a new audio cue"""
        cue = AudioCue(
            id=str(uuid.uuid4()),
            name=name,
            track=track,
            trigger_condition=trigger_condition,
            volume=volume,
            delay_seconds=delay_seconds,
            created_by=created_by,
            created_at=datetime.utcnow()
        )
        
        self.cues[cue.id] = cue
        return cue.id
    
    async def trigger_cue(self, cue_id: str, player: AudioPlayer) -> bool:
        """Trigger an audio cue"""
        if cue_id not in self.cues:
            return False
        
        cue = self.cues[cue_id]
        
        # Apply delay if specified
        if cue.delay_seconds > 0:
            trigger_time = datetime.utcnow() + timedelta(seconds=cue.delay_seconds)
            self.scheduled_cues.append((trigger_time, cue))
            return True
        
        # Play immediately
        original_volume = player.channel_volumes['sfx']
        player.channel_volumes['sfx'] *= cue.volume
        
        success = await player.play_track(cue.track, channel='sfx')
        
        # Restore original volume after track duration
        asyncio.create_task(
            self._restore_volume_after_delay(player, original_volume, cue.track.duration)
        )
        
        return success
    
    async def _restore_volume_after_delay(self, player: AudioPlayer,
                                         original_volume: float, delay: float):
        """Restore channel volume after cue finishes"""
        await asyncio.sleep(delay)
        player.channel_volumes['sfx'] = original_volume
    
    async def process_scheduled_cues(self, player: AudioPlayer):
        """Process any scheduled cues that are ready"""
        now = datetime.utcnow()
        ready_cues = []
        
        for trigger_time, cue in self.scheduled_cues:
            if trigger_time <= now:
                ready_cues.append((trigger_time, cue))
        
        for trigger_time, cue in ready_cues:
            await self.trigger_cue(cue.id, player)
            self.scheduled_cues.remove((trigger_time, cue))


class AudioAmbianceService:
    """Main audio ambiance service"""
    
    def __init__(self):
        self.players: Dict[str, AudioPlayer] = {}  # One per session
        self.playlist_managers: Dict[str, PlaylistManager] = {}
        self.ambiance_managers: Dict[str, AmbianceManager] = {}
        self.cue_managers: Dict[str, AudioCueManager] = {}
        
        self.session_states: Dict[str, Dict[str, Any]] = {}
        self._background_tasks: Dict[str, asyncio.Task] = {}
    
    async def initialize_session_audio(self, session: SessionSchema) -> bool:
        """Initialize audio system for a session"""
        try:
            self.players[session.id] = AudioPlayer()
            self.playlist_managers[session.id] = PlaylistManager()
            self.ambiance_managers[session.id] = AmbianceManager()
            self.cue_managers[session.id] = AudioCueManager()
            
            self.session_states[session.id] = {
                "current_playlist": None,
                "current_scene": None,
                "shuffle": False,
                "volume": {
                    "master": 1.0,
                    "music": 0.7,
                    "ambiance": 0.5,
                    "sfx": 0.8
                }
            }
            
            # Start background task for scheduled cues
            self._background_tasks[session.id] = asyncio.create_task(
                self._background_processor(session.id)
            )
            
            return True
        
        except Exception as e:
            print(f"Error initializing session audio: {e}")
            return False
    
    async def _background_processor(self, session_id: str):
        """Background task for processing scheduled cues and other tasks"""
        while session_id in self.players:
            try:
                # Process scheduled cues
                cue_manager = self.cue_managers.get(session_id)
                player = self.players.get(session_id)
                
                if cue_manager and player:
                    await cue_manager.process_scheduled_cues(player)
                
                await asyncio.sleep(0.1)  # Check every 100ms
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in background processor for session {session_id}: {e}")
                await asyncio.sleep(1.0)
    
    async def play_music(self, session_id: str, track_id: str = None,
                        playlist_id: str = None, crossfade: bool = True) -> bool:
        """Play music track or from playlist"""
        if session_id not in self.players:
            return False
        
        player = self.players[session_id]
        playlist_manager = self.playlist_managers[session_id]
        
        track = None
        
        if playlist_id:
            if await playlist_manager.load_playlist(playlist_id):
                track = await playlist_manager.get_next_track(
                    shuffle=self.session_states[session_id]["shuffle"]
                )
        elif track_id:
            # Load individual track (implementation would fetch from database)
            pass
        
        if track:
            if crossfade and player.current_track:
                return await player.crossfade_to(track)
            else:
                return await player.play_track(track, channel='music', loop=False)
        
        return False
    
    async def set_ambiance_scene(self, session_id: str, scene_id: str,
                                fade_duration: float = 2.0) -> bool:
        """Set the ambiance scene for a session"""
        if session_id not in self.players:
            return False
        
        player = self.players[session_id]
        ambiance_manager = self.ambiance_managers[session_id]
        
        success = await ambiance_manager.activate_scene(scene_id, player, fade_duration)
        
        if success:
            self.session_states[session_id]["current_scene"] = scene_id
        
        return success
    
    async def trigger_audio_cue(self, session_id: str, cue_name: str) -> bool:
        """Trigger an audio cue"""
        if session_id not in self.players:
            return False
        
        player = self.players[session_id]
        cue_manager = self.cue_managers[session_id]
        
        # Find cue by name
        for cue_id, cue in cue_manager.cues.items():
            if cue.name == cue_name:
                return await cue_manager.trigger_cue(cue_id, player)
        
        return False
    
    async def set_volume(self, session_id: str, channel: str, volume: float) -> bool:
        """Set volume for a specific audio channel"""
        if session_id not in self.players:
            return False
        
        player = self.players[session_id]
        
        if channel == "master":
            await player.set_volume(volume)
            self.session_states[session_id]["volume"]["master"] = volume
        else:
            player.channel_volumes[channel] = volume
            await player.set_volume(player.volume, channel)
            self.session_states[session_id]["volume"][channel] = volume
        
        return True
    
    async def get_session_audio_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get current audio state for a session"""
        if session_id not in self.session_states:
            return None
        
        player = self.players[session_id]
        state = self.session_states[session_id].copy()
        
        state.update({
            "playback_state": player.state.value,
            "current_track": player.current_track.dict() if player.current_track else None,
            "playback_position": player.get_playback_position()
        })
        
        return state
    
    async def cleanup_session_audio(self, session_id: str):
        """Clean up audio resources for a session"""
        # Cancel background task
        if session_id in self._background_tasks:
            self._background_tasks[session_id].cancel()
            del self._background_tasks[session_id]
        
        # Clean up player
        if session_id in self.players:
            self.players[session_id].cleanup()
            del self.players[session_id]
        
        # Clean up managers
        for manager_dict in [
            self.playlist_managers,
            self.ambiance_managers,
            self.cue_managers,
            self.session_states
        ]:
            if session_id in manager_dict:
                del manager_dict[session_id]
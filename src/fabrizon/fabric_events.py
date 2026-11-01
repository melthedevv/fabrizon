"""Fabric API event-to-site mapping for Horizon.

Many Fabric mods use Fabric API events instead of direct mixins. These events are
implemented by Fabric API's own mixins (in nested jars). This module maps
event callback methods to the Horizon hook points they correspond to.

When a mod references a Fabric API event, Fabrizon can now suggest the
corresponding Horizon target instead of just listing the event class.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EventMapping:
    """Maps a Fabric API event callback to a Horizon hook point."""
    event_class: str          # e.g., "net/fabricmc/fabric/api/client/event/lifecycle/v1/ClientTickEvents$StartTick"
    callback_method: str      # e.g., "onStartTick"
    horizon_kind: str         # "HEAD", "RETURN", etc.
    horizon_target: str       # e.g., "horizon_core::client::tick::on_start_tick"
    notes: str = ""


# Fabric API event -> Horizon hook point mappings.
# Source: Fabric API source code + horizon-mixins docs.
# Only events with known Horizon counterparts are listed.
_EVENT_MAP: list[EventMapping] = [
    # ClientTickEvents
    EventMapping(
        "net/fabricmc/fabric/api/client/event/lifecycle/v1/ClientTickEvents$StartTick",
        "onStartTick",
        "HEAD",
        "horizon_core::client::tick::on_start_tick",
        "Called at start of client tick",
    ),
    EventMapping(
        "net/fabricmc/fabric/api/client/event/lifecycle/v1/ClientTickEvents$EndTick",
        "onEndTick",
        "HEAD",
        "horizon_core::client::tick::on_end_tick",
        "Called at end of client tick",
    ),

    # ServerTickEvents
    EventMapping(
        "net/fabricmc/fabric/api/event/lifecycle/v1/ServerTickEvents$StartTick",
        "onStartTick",
        "HEAD",
        "horizon_core::server::tick::on_start_tick",
        "Called at start of server tick",
    ),
    EventMapping(
        "net/fabricmc/fabric/api/event/lifecycle/v1/ServerTickEvents$EndTick",
        "onEndTick",
        "HEAD",
        "horizon_core::server::tick::on_end_tick",
        "Called at end of server tick",
    ),

    # ServerLifecycleEvents
    EventMapping(
        "net/fabricmc/fabric/api/event/lifecycle/v1/ServerLifecycleEvents$ServerStarted",
        "onServerStarted",
        "HEAD",
        "horizon_core::server::lifecycle::on_server_started",
        "Server fully started",
    ),
    EventMapping(
        "net/fabricmc/fabric/api/event/lifecycle/v1/ServerLifecycleEvents$ServerStopping",
        "onServerStopping",
        "HEAD",
        "horizon_core::server::lifecycle::on_server_stopping",
        "Server shutting down",
    ),

    # ClientPlayConnectionEvents
    EventMapping(
        "net/fabricmc/fabric/api/client/networking/v1/ClientPlayConnectionEvents$Join",
        "onPlayReady",
        "HEAD",
        "horizon_core::client::connection::on_play_ready",
        "Client joined a server",
    ),
    EventMapping(
        "net/fabricmc/fabric/api/client/networking/v1/ClientPlayConnectionEvents$Disconnect",
        "onDisconnect",
        "HEAD",
        "horizon_core::client::connection::on_disconnect",
        "Client disconnected from server",
    ),

    # ServerPlayConnectionEvents
    EventMapping(
        "net/fabricmc/fabric/api/networking/v1/ServerPlayConnectionEvents$Join",
        "onPlayReady",
        "HEAD",
        "horizon_core::server::connection::on_play_ready",
        "Player joined server",
    ),
    EventMapping(
        "net/fabricmc/fabric/api/networking/v1/ServerPlayConnectionEvents$Disconnect",
        "onDisconnect",
        "HEAD",
        "horizon_core::server::connection::on_disconnect",
        "Player disconnected",
    ),

    # CommandRegistrationCallback
    EventMapping(
        "net/fabricmc/fabric/api/command/v2/CommandRegistrationCallback",
        "register",
        "HEAD",
        "horizon_core::command::registration::register_commands",
        "Register custom commands",
    ),

    # HudElementRegistry
    EventMapping(
        "net/fabricmc/fabric/api/client/rendering/v1/hud/HudElementRegistry",
        "register",
        "HEAD",
        "horizon_core::client::hud::register_element",
        "Register HUD element",
    ),

    # KeyMappingHelper
    EventMapping(
        "net/fabricmc/fabric/api/client/keymapping/v1/KeyMappingHelper",
        "registerKeyBinding",
        "HEAD",
        "horizon_core::client::input::register_key_binding",
        "Register key binding",
    ),

    # ClientCommandRegistrationCallback
    EventMapping(
        "net/fabricmc/fabric/api/client/command/v2/ClientCommandRegistrationCallback",
        "register",
        "HEAD",
        "horizon_core::client::command::registration::register_commands",
        "Register client commands",
    ),

    # PayloadTypeRegistry
    EventMapping(
        "net/fabricmc/fabric/api/networking/v1/PayloadTypeRegistry",
        "register",
        "HEAD",
        "horizon_core::networking::payload::register_type",
        "Register custom payload type",
    ),

    # EntityAttributeCreationCallback
    EventMapping(
        "net/fabricmc/fabric/api/event/entity/EntityAttributeCreationCallback",
        "register",
        "HEAD",
        "horizon_core::entity::attributes::register_attributes",
        "Register entity attributes",
    ),
]


def find_event_mapping(event_class: str, callback_method: str | None = None) -> EventMapping | None:
    """Find a mapping for a Fabric API event class and optional callback method."""
    # Normalize inner class separator
    norm = event_class.replace("/", ".").replace("$", ".")
    for m in _EVENT_MAP:
        if m.event_class.replace("/", ".").replace("$", ".") == norm:
            if callback_method is None or m.callback_method == callback_method:
                return m
    return None


def find_by_fabric_api_ref(ref: str) -> EventMapping | None:
    """Find mapping from a Fabric API class reference (e.g., from class_refs)."""
    # ref is like "net/fabricmc/fabric/api/client/event/lifecycle/v1/ClientTickEvents$StartTick"
    return find_event_mapping(ref)


def all_event_mappings() -> list[EventMapping]:
    return list(_EVENT_MAP)


def fabric_api_refs_to_horizon(refs: list[str]) -> list[tuple[str, EventMapping]]:
    """Convert a list of Fabric API class references to (ref, mapping) pairs."""
    out: list[tuple[str, EventMapping]] = []
    for ref in refs:
        m = find_by_fabric_api_ref(ref)
        if m:
            out.append((ref, m))
    return out
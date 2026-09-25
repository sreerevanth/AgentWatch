"""AgentWatch v3 sensors.

Sensors capture raw observations (payload + identifiers declared by the source) and
hand them to a sink. They never interpret behaviour, never block and never raise into
the observed application.
"""

from agentwatch.sensors.base import (
    FileSink,
    HttpSink,
    ListSink,
    ObservationSink,
    Sensor,
    SensorContext,
)

__all__ = ["FileSink", "HttpSink", "ListSink", "ObservationSink", "Sensor", "SensorContext"]

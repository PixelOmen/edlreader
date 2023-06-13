from pathlib import Path
from copy import deepcopy
from dataclasses import dataclass

from .libs import tclib3

@dataclass
class EDLEvent:
    event_number: int
    reel_name: str
    channel: str
    transition: str
    source_in: str
    source_out: str
    record_in: str
    record_out: str
    marker: "EDLMarker"
    notes: list[str]


    def __str__(self) -> str:
        partone = f"{self.event_number}  {self.reel_name}     {self.channel}"
        parttwo = f"     {self.transition}        "
        partthree = f"{self.source_in} {self.source_out} {self.record_in} {self.record_out}"
        return partone + parttwo + partthree


@dataclass
class EDLMarker:
    color: str
    name: str
    duration: str

    def __post_init__(self):
        self.color = self.color[2:].strip()
        self.name = self.name[2:].strip()
        self.duration = self.duration[2:].strip()

@dataclass
class Metadata:
    name: str = ""
    prevon: tuple[str, str]=("", "")
    maintitle: tuple[str, str]=("", "")
    nexton: tuple[str, str]=("", "")
    livingcreds: tuple[str, str]=("", "")
    endcreds: tuple[str, str]=("", "")
    textless: tuple[str, str]=("", "")
    colors = {
        "ResolveColorBlue" : "prevon",
        "ResolveColorCyan" : "maintitle",
        "ResolveColorGreen" : "nexton",
        "ResolveColorYellow" : "livingcreds",
        "ResolveColorRed" : "endcreds",
        "ResolveColorPink" : "textless",
    }

    def set(self, edlreader: "EDLReader") -> None:
        """
        Sets all values of Metadata object using an EDLReader instance.
        """
        self.name = edlreader.edl_path.name
        # if len(edlreader.current_events) != 6:
        #     raise AttributeError("Not enough markers to create Metadata")
        colors = self.colors
        for event in edlreader.current_events:
            if edlreader.df:
                rec_in = event.record_in[:8] + ";" + event.record_in[9:]
            else: 
                rec_in = event.record_in
            attr = colors[event.marker.color]
            recin_frames = tclib3.tc_to_frames(rec_in, edlreader.fps)
            dur = int(event.marker.duration) - 1
            recout = tclib3.frames_to_tc(recin_frames + dur, edlreader.fps, edlreader.df)
            setattr(self, attr, (event.record_in, recout))

    def __str__(self) -> str:
        return f"{self.name},{self.prevon[0]}-{self.prevon[1]},{self.maintitle[0]}-{self.maintitle[1]},{self.nexton[0]}-{self.nexton[1]},{self.livingcreds[0]}-{self.livingcreds[1]},{self.endcreds[0]}-{self.endcreds[1]},{self.textless[0]}-{self.textless[1]}\n"


class EDLReader:
    def __init__(self, edl_path: Path, fps: float, resolvemarkers: bool=False, df: bool=False) -> None:
        self.edl_path = edl_path
        self.fps = fps
        self.df = df
        self.resolvemarkers = resolvemarkers
        self.edl_lines = self._read()
        self.header: list[str] = []
        self.original_events: list[EDLEvent] = []
        self._parse()
        self.current_events: list[EDLEvent] = deepcopy(self.original_events)

    def write(self, path: str | Path) -> None:
        with open(path, "w") as fp:
            for line in self.header:
                fp.write(f"{line}\n")
            fp.write("\n")
            for event in self.current_events:
                fp.write(f"{str(event)}\n")
                for note in event.notes:
                    fp.write(f"{note}\n")
                fp.write("\n")
            

    def reset(self) -> None:
        self.current_events: list[EDLEvent] = deepcopy(self.original_events)

    def timecodes(self, src_tc: bool=False) -> list[str]:
        tc = []
        for event in self.current_events:
            if src_tc:
                tc.append(event.source_in)
                tc.append(event.source_out)
            else:
                tc.append(event.record_in)
                tc.append(event.record_out)
        return tc


    def offset_forward(self, offset: str, frames: bool=False, offset_src: bool=False) -> None:
        """
        Offsets EDL current events. 'offset' takes SMPTE TC or frames as string.
        Set 'frames' to 'True' if using frames for 'offset'.
        Only modifies record timecode unless 'offset_src' is 'True'
        """
        if frames:
            offset_frames = int(offset)
        else:
            offset_frames = tclib3.tc_to_frames(offset, self.fps)
        
        for event in self.current_events:
            if offset_src:
                event.source_in = self._offset(event.source_in, offset_frames)
                event.source_out = self._offset(event.source_out, offset_frames)
            event.record_in = self._offset(event.record_in, offset_frames)
            event.record_out = self._offset(event.record_out, offset_frames)

    def offset_backward(self, offset: str, frames: bool=False, offsetsrc_tc: bool=False) -> None:
        if frames:
            offset_frames = int(offset)
        else:
            offset_frames = tclib3.tc_to_frames(offset, self.fps)
        
        for event in self.current_events:
            if offsetsrc_tc:
                event.source_in = self._offset(event.source_in, offset_frames, True)
                event.source_out = self._offset(event.source_out, offset_frames, True)
            event.record_in = self._offset(event.record_in, offset_frames, True)
            event.record_out = self._offset(event.record_out, offset_frames, True)            

    def _offset(self, tc: str, offset: int, subtract: bool=False) -> str:
        frames = tclib3.tc_to_frames(tc, self.fps)
        if subtract:
            new_frames = frames - offset
            new_frames = 0 if new_frames < 0 else new_frames
        else:
            new_frames = frames + offset
        return tclib3.frames_to_tc(new_frames,self.fps, self.df)

    def _read(self) -> list[str]:
        with open(self.edl_path, "r") as fp:
            edl_lines = fp.readlines()
        stripped_lines = [l.strip("\n") for l in edl_lines if l != "\n"]
        return stripped_lines

    def _parse(self) -> None:
        events = []
        comment_lines = []
        current_event = []
        is_event = False
        is_header = True
        header = []
        for line in self.edl_lines:
            if is_event and line[0].isdigit():
                current_event.append(comment_lines)
                events.append(current_event)
                comment_lines = []
                current_event = []
                is_event = False
            if is_event:
                comment_lines.append(line)
            if line[0].isdigit():
                split_line = line.split(" ")
                split_line = [section for section in split_line if section]
                current_event.append(split_line)
                is_event = True
                is_header = False
            elif is_header:
                header.append(line)
        if current_event and comment_lines:
            current_event.append(comment_lines)
        if current_event:
            events.append(current_event)

        edl_events = []
        for event in events:
            if self.resolvemarkers:
                markerstr = event[1][0].split("|")[1:]
                marker = EDLMarker(*markerstr)
                edlevent = EDLEvent(*event[0], marker=marker, notes=event[1])
                edl_events.append(edlevent)
            else:
                edlevent = EDLEvent(*event[0], marker=EDLMarker("","",""), notes=event[1])
                edl_events.append(edlevent)

        self.original_events = edl_events
        self.header = header
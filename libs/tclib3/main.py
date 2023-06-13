from audioop import mul
from . import helpers

def frames_to_tc(totalframes: int, fps: float=24, dropframe: bool=False):
    helpers.test_support(fps)

    totalframes = helpers.adjust_df_frames(totalframes, fps, True) if dropframe else totalframes
    hrs, mins, secs, frames = helpers.frames_to_tuple(totalframes, fps)

    tcints=[hrs,mins,secs,frames]
    tcstrings = [helpers.prezero(tc) for tc in tcints]
    formattedtc = ":".join(tcstrings)

    if dropframe:
        helpers.is_valid_df_frame(mins, secs, frames, fps, True)
        formattedtc = formattedtc[0:8] + ";" + formattedtc[9:]

    return formattedtc


def frames_to_ms(frames: int, fps: float=24, hrminsec: bool=False):
    helpers.test_support(fps)

    fps = float(fps)
    if fps.is_integer():
        framems = 1000/fps
    else:
        fps = (round(fps)*1000) / 1001
        framems = 1000/fps

    totalms = frames * framems
    if hrminsec:
        totalsecs = totalms / 1000
        hrs = int(totalsecs / 3600)
        remaining_secs = totalsecs % 3600
        mins = int(remaining_secs / 60)
        secs = round(remaining_secs % 60, 4)
        return [hrs, mins, secs]
    return totalms


def tc_to_frames(tcstr: str, fps: float):
    helpers.test_support(fps)

    if ";" in tcstr:
        helpers.test_dropframe(fps)
        df = True
    else:
        df = False

    clean_tcstr = tcstr.replace(";", ":")
    tcsplit = clean_tcstr.split(":")

    hrs = int(tcsplit[0])
    mins = int(tcsplit[1])
    secs = int(tcsplit[2])
    frames = int(tcsplit[3])

    fps_round = round(fps)
    if df:
        helpers.is_valid_df_frame(mins, secs, frames, fps, True)
        _, multiplier = helpers.test_dropframe(fps)
        totalmins = (hrs * 60) + mins
        non_dropped_frames = int(int(totalmins) / 10) * multiplier
        dropped_Frames = totalmins * multiplier
        total_dropped = dropped_Frames - non_dropped_frames
        total_ndf = (hrs * 3600 * fps_round) + (mins * 60 * fps_round) + (secs * fps_round) + frames
        totalframes = total_ndf - total_dropped
        return totalframes
    else:
        return (hrs * 3600 * fps_round) + (mins * 60 * fps_round) + (secs * fps_round) + frames


def ms_to_frames(ms, fps=24, hrminsec=False):
    helpers.test_support(fps)

    fps = float(fps)
    if fps.is_integer():
        framems = 1000/fps
    else:
        fps = (round(fps)*1000) / 1001
        framems = 1000/fps

    if hrminsec:
        ms = (ms[0]*3600 + ms[1]*60 + ms[2]) * 1000

    frames = round(ms/framems)
    return frames

def duration(start_tc: str, end_tc: str, fps: float, dropframe: bool=False) -> str:
    start_frames = tc_to_frames(start_tc, fps)
    end_frames = tc_to_frames(end_tc, fps)
    return frames_to_tc(end_frames-start_frames, fps, dropframe)
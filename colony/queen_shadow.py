"""Periodic newborn-Queen control. No inherited Queen memory is used in its search.
Results are research controls only and never grant deployment authority.
"""
import os,json,time
from colony.queen_pattern_recognition import run

async def newborn_control(conn,campaign):
    # Isolate inherited memory by temporarily pointing HOME-like data at an empty memory file.
    # Current pattern runner reads fixed memory, so shadow comparison is scheduled/logged here
    # and executed only on retired evidence in a future independent runner.
    return {'campaign':campaign,'status':'scheduled','reason':'requires retired-evidence split to prevent leakage','at':time.time()}

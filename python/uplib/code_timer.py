# code_timer.py
#
# This file is part of the "UpLib 1.7.11" release.
# Copyright (C) 2003-2011  Palo Alto Research Center, Inc.
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
  # Ported from CodeTimerImpl.mesa and CodeTimerConcrete.mesa in the Cedar environment.
  # Bier, March 19, 1998 5:21 pm PST
  #
  # Contents:  Routines for maintaining a table of average times for user-specified
  # operations.  This module keeps track of the nesting of code blocks so that it
  # can provide an informative print-out later.  It sorts statistics by python thread
  # so as to properly report statistics about multi-threaded programs.
  
  # Clients of this package will most likely be interested in routines:
  # StartInterval, StartInt, StopInterval, StopInt, PrintTable, and perhaps
  # CreateTable, GetTable, ResetTable, ResetInterval, and
  # SetIntMilliseconds

import time
import uplib.static as static
from uplib.plibUtil import uthread as thread
import sys

class Table:
  name = 'default' # the name of table as a string
  processes = [] # a list of the form [ProcessPair1, ProcessPair2, ... ]
  def __init__ (self, name, processes):
    self.name = name
    self.processes = processes
  
# Each ProcessPair1 describes the outer block of code and the current block of
# code that we have entered and not exited for a particular thread.  This allows
# us to make sense of nested code blocks even in multi-threaded code.

class ProcessPair:
  outer = None # An IntervalInContext
  current = None # An IntervalInContext
  process = None # A python thread
  
class IntervalInContext:
  name = 'default' # name of this code interval
  starts = 0
  stops = 0
  prematureStops = 0
  prematureStopName = None # a unique string
  startTime = 0 # in seconds (if we can't figure out how to do milliseconds)
  totalTime = 0
  maxTime = 0
  maxIndex = 0
  minTime = 0x7FFFFFFF # the largest positive 32-bit integer
  children = [] # a list of IntervalInContext.  The intervals that were started when
      # this interval was table.current
  parent = None # The interval that was table.current when this interval began

#c = static._get('c')
#c.TablesRef = {}

#c.intervalPool = [None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None] # A maximum of 25 IntervalInContext's
#c.intervalPoolMax = 25
#c.intervalPoolIndex = -1

Problem = "CodeTimerProblem" # Called with a string-value message

# Getting ready to test performance.
# 
def CreateIntervalInContext(intervalName):
    # returns an IntervalInContext
    intervalInContext = IntervalInContext()
    intervalInContext.name = intervalName
    return intervalInContext
  
def AllocateIntervalInternal(intervalName, c):
  # returns (interval: IntervalInContext):
  if c.intervalPoolIndex >= 0:
    interval = c.intervalPool[c.intervalPoolIndex]
    ZeroInterval(interval)
    interval.children = []
    interval.name = intervalName
    c.intervalPoolIndex = c.intervalPoolIndex - 1
  else: interval = CreateIntervalInContext(intervalName)
  return interval
  
def FreeIntervalInternal(interval, c):
  if c.intervalPoolIndex < c.intervalPoolMax -1:
    c.intervalPoolIndex = c.intervalPoolIndex + 1
    c.intervalPool[c.intervalPoolIndex] = interval
  interval.children = []
  interval.parent = None
  
def CreateTable(name = "NoName"):
  # returns (table):
  oldTable = GetTable(name)
  if oldTable == None:
    # outer = AllocateInterval('Outer')
    table = Table(name, [])
    if name != "NoName": AddTableToTables(table)
  else:
    table = oldTable
    ResetTable(table)
  return table
  
def GetTable(name):
  # returns (table):
  c = static._get('c')
  if c.TablesRef.has_key(name): table = c.TablesRef[name]
  else: table = None
  return table
  
def AddTableToTables(table):
  c = static._get('c')
  if c.TablesRef.has_key(table.name): raise "ERROR"
  c.TablesRef[table.name] = table
  
def ResetTable(table):
  # This routine may need to be locked in general to support multiple threads
  # The table is a tree of nested intervals.  Return all of these intervals to the
  # interval pool except for the top level interval
  c = static._get('c')
  for pair in table.processes:
    for child in pair.outer.children:
      FreeIntervalAndChildren(child, c)
    pair.outer.children = []
    pair.current = pair.outer
  table.processes = []
  
def FreeIntervalAndChildren(interval, c):
  for child in interval.children:
    FreeIntervalAndChildren(child, c)
  FreeIntervalInternal(interval, c)
  
def ResetInterval(intervalName, table):
  # This routine may need to be locked in general to support multiple threads.
  # Wherever this interval occurs in the tree, zero it and its children.
  for pair in table.processes:
    ZeroNamedIntervalInTree(intervalName, pair.outer)
  
def ZeroNamedIntervalInTree(intervalName, interval):
  if interval.name == intervalName: ZeroInterval(interval)
  for child in interval.children:
    ZeroNamedIntervalInTree(intervalName, child)
  
def ZeroInterval(interval):
  interval.starts = 0
  interval.stops = 0
  interval.prematureStops = 0
  interval.prematureStopName = None
  interval.startTime = 0
  interval.totalTime = 0
  interval.maxTime = 0
  interval.minTime = 0x7FFFFFFF
  
# c.codeTimerOn = 0
noteThreads = 0

def FindChildIntervalInContext(intervalName, context):
  # returns (interval: IntervalInContext = None):
  for child in context.children:
    if child.name == intervalName: return child
  return None
  
defaultProcess = None # initialized in Init() below

def GetPairForProcess(table, c):
  # returns (pp: ProcessPair):
  global noteThreads
  if noteThreads:
    process = thread.get_ident()
    for pair in table.processes: # pair is a ProcessPair
      if pair.process == process: return pair
    pp = AddProcessPair(table, process, c)
  else:
    if table.processes == None or (len(table.processes) == 0):
      pp = AddProcessPair(table, defaultProcess, c)
    else: pp = table.processes[0]
  return pp
  
def AddProcessPair(table, process, c):
  # returns (pair: ProcessPair):
  pair = ProcessPair()
  pair.current = pair.outer = AllocateIntervalInternal('Outer', c)
  pair.process = process
  table.processes = [pair]+table.processes
  return pair
  
def StartInterval(intervalName, table, c=None):
  # To work properly in multi-threaded code, this may need to be guarded
  # by a lock.  For now, we use the fact that 'c.' variables are thread-safe.
  #
  # We have encountered the beginning of a new interval.  Add a representation
  # for it as a child of the most recently entered active interval.
  if not c: c = static._get('c')
  interval = IntervalInContext()
  current = IntervalInContext()
  pair = ProcessPair()
  
  if not c.has_key('codeTimerOn'): return # can occur if StartInt is called from a
      # new thread that has never initialized code_timer.  In this case, assume
      # code timing should be turned off.
  if not c.codeTimerOn: return
  pair = GetPairForProcess(table, c)
  current = pair.current
  interval = FindChildIntervalInContext(intervalName, current)
  if interval == None:
    interval = AllocateIntervalInternal(intervalName, c)
    current.children = current.children+[interval]
    interval.parent = current

  interval.starts = interval.starts + 1
  interval.startTime = time.time()
  pair.current = interval

  
def StartInt(intervalName, tableName):
  c = static._get('c')
  if not c.has_key('codeTimerOn'): return # can occur if StartInt is called from a
      # new thread that has never initialized code_timer.  In this case, assume
      # code timing should be turned off.
  if not c.codeTimerOn: return
  table = GetTable(tableName)
  if table == None: table = CreateTable(tableName)
  StartInterval(intervalName, table, c)
  
  
def StopInterval(intervalName, table, c=None):
  # This procedure may need to be locked to handle threads properly.
  if not c: c = static._get('c')
  interval = IntervalInContext()
  pair = ProcessPair()
  stopTime = elapsedTime = 0
  
  if not c.has_key('codeTimerOn'): return # can occur if StartInt is called from a
      # new thread that has never initialized code_timer.  In this case, assume
      # code timing should be turned off.
  if not c.codeTimerOn: return
  stopTime = time.time()
  pair = GetPairForProcess(table, c)
  interval = pair.current
  if interval.name == intervalName: # normal case
    # The current interval has come to an end.
    interval.stops = interval.stops + 1
    elapsedTime = stopTime - interval.startTime
    interval.totalTime = interval.totalTime + elapsedTime
    if elapsedTime < interval.minTime: interval.minTime = elapsedTime
    if elapsedTime > interval.maxTime:
      interval.maxTime = elapsedTime
      interval.maxIndex = interval.starts
    if interval.parent != None: pair.current = interval.parent
  else: # encountered a stop while a different interval is active
    interval.prematureStops = interval.prematureStops + 1
    if interval.prematureStops == 1: interval.prematureStopName = intervalName
  
def StopInt(intervalName, tableName):  
  c = static._get('c')
  if not c.has_key('codeTimerOn'): return # can occur if StartInt is called from a
      # new thread that has never initialized code_timer.  In this case, assume
      # code timing should be turned off.
  if not c.codeTimerOn: return
  table = GetTable(tableName)
  if table == None: table = CreateTable(tableName)
  StopInterval(intervalName, table, c)
  
"""
def SetIntMilliseconds: ENTRY PROC (intervalName, startTime: CARD32, stopTime: CARD32, tableName):
  # This call is equivalent to a StartInt, followed stopTime-startTime later by a StopInt.
  period: INT32
  table
  interval = IntervalInContext()
  current = IntervalInContext()
  pair = ProcessPair()
  
  InnerProc: PROC == { # workaround for 4.1 C optimizer bug JKF 2/21/90
    if not c.codeTimerOn: return
    period = Period(startTime, stopTime)
    table = GetTable(tableName)
    if table == None: table = CreateTable(tableName)
    
    pair = GetPairForProcess(table, c)
    current = pair.current
    interval = FindChildIntervalInContext(intervalName, current)
    if interval == None:
      interval = AllocateIntervalInternal(intervalName, c)
      current.children = CONS(interval, current.children)
      interval.parent = current
      }
    if period > 0:
      posPer: CARD32 = period
      pulses: CARD32 = BasicTime.MicrosecondsToPulses(posPer*1000)
      interval.starts = interval.starts + 1
      interval.stops = interval.stops + 1
      interval.totalTime = interval.totalTime + pulses
      interval.minTime = if pulses < interval.minTime: pulses else: interval.minTime
      if pulses > interval.maxTime:
        interval.maxTime = pulses
        interval.maxIndex = interval.stops
        }
      }
    else:
      interval.prematureStops = interval.prematureStops + 1
      interval.prematureStopName = 'NegativeTimePeriod'
      }
    }; # InnerProc
  InnerProc()
  }
"""
  
def Period(begin, end):
  # returns (INT32) in milliseconds
  return (end-begin)
  
# 
# Printing results.

"""
def ForEachTable(proc: ForEachTableProc):
  # returns (aborted: BOOL = FALSE):
  # Enumerates all of the CodeTimer tables in the current virtual address space.  If the proc ever returns done=TRUE, then and only then aborted will be TRUE.
  DoForEachTable: RefTab.EachPairAction == {
    # PROC (key: Key, val: Val)
    # returns (quit: BOOL _ FALSE)
    tableName = NARROW(key)
    table = NARROW(val)
    quit = proc(tableName, table)
    }
  aborted = RefTab.Pairs(c.TablesRef, DoForEachTable)
  }
ForEachTableProc: TYPE == CodeTimer.ForEachTableProc
# ForEachTableProc: TYPE == PROC (table)
    # returns (done: BOOL _ FALSE)
"""

def ForEachIntervalInContext(f, table, proc):
  # returns (aborted: BOOL = FALSE):
  # Walks the tree of intervals.  The first level of this tree consists of those intervals
  # that were called when no other intervals were active.  The children of each
  # interval are the intervals that were called while that interval was active.  Thus,
  # each named code interval may appear several times in the tree, once for each
  # interval that called it.  Each appearance is called an interval-in-context.
  aborted = 0
  processCount = 0
  if table == None: return aborted
  if len(table.processes) > 1: multi_threads = 1
  else: multi_threads = 0
  for pair in table.processes:
    for child in pair.outer.children:
      aborted = WalkInterval(f, processCount, child, proc, multi_threads, 0)
      if aborted: return aborted
    processCount = processCount + 1
  return aborted

def PulsesToMilliseconds(time_float):
    # current time is a floating point number of seconds
    if time_float == 0x7FFFFFFF: return time_float
    try:
        msecs = time_float * 1000
    except OverflowError:
        # raise 'PulsesToMilliseconds OverflowError, time_float = %d' % time_float
        msecs = 0x7FFFFFFF
    except:
        msecs = 0x7FFFFFFF
    return msecs

def WalkInterval(f, process, interval, proc, multi_threads, level):
  # returns (aborted: BOOL = FALSE):
  totalMsec = PulsesToMilliseconds(interval.totalTime)
  minMsec = PulsesToMilliseconds(interval.minTime)
  maxMsec = PulsesToMilliseconds(interval.maxTime)
  aborted = proc(f, interval.name, process, interval.starts, totalMsec, minMsec, maxMsec, interval.maxIndex, interval.starts - interval.stops, interval.prematureStops, interval.prematureStopName, multi_threads, level)
  if aborted: return aborted
  for child in interval.children:
    aborted = WalkInterval(f, process, child, proc, multi_threads, level+1)
    if aborted: return aborted
  return aborted
  
def DoPrintIntervalInContext(f, intervalName, process, starts, totalMsec, minMsec, maxMsec, maxIndex, startsWithoutStops, prematureStops, prematureStopName, multi_threads, level = 0):
    # returns (done: BOOL _ FALSE]
    done = 0
    if starts != 0:
      for i in range(1, level+1): f.write("  ") # indent
      if startsWithoutStops > 0: f.write("***") # call attention to broken intervals
      if prematureStops > 0: f.write("###") # got a stop for wrong interval
      if multi_threads:
        f.write("%d.%s. n: %d. tot: %d. " % (process, intervalName, starts, totalMsec))
      else:
        f.write("%s. n: %d. tot: %d. " % (intervalName, starts, totalMsec))
      avgMsec = totalMsec/starts
      if prematureStops > 0:
        f.write("avg: %d. range: [%d..%d], worst: %d, bad_stops: %d at %s\n" % (avgMsec, minMsec, maxMsec, maxIndex, prematureStops, prematureStopName))
      elif startsWithoutStops > 0:
        f.write("avg: %d. range: [%d..%d], worst: %d, no_stops: %d\n" % (avgMsec, minMsec, maxMsec, maxIndex, startsWithoutStops))
      else:
        f.write("avg: %d. range: [%d..%d], worst: %d\n" % (avgMsec, minMsec, maxMsec, maxIndex))
    return done
    
def PrintTable(f, table_name):
  table = GetTable(table_name)
  if table == None: return
  done = ForEachIntervalInContext(f, table, DoPrintIntervalInContext)
  
def PrintTableHTML(f, table_name):
  table = GetTable(table_name)
  if table == None: return
  f.write('<pre>\n')
  c = static._get('c')
  if (not c.has_key('codeTimerOn')) or (not c.codeTimerOn):
    f.write("<!-- Code Timer appears to be turned off.  To see results, make sure you have")
    f.write(" called code_timer.CodeTimerOn(). -->");
  else:
    f.write("Code Timer performance times in milliseconds:");
  done = ForEachIntervalInContext(f, table, DoPrintIntervalInContext)
  f.write('</pre>\n')

"""  
def PrintIntervalInContext(f: IO.STREAM, process, interval: IntervalInContext, nestingLevel: NAT = 0, children: BOOL = FALSE):
  name: Rope.ROPE
  totalTime, avgTime, minTime, maxTime: LONG CARDINAL
  if interval.starts # 0:
    for i: NAT IN [1..nestingLevel] DO f.PutRope["  "]; ENDLOOP; # indent
    name = Atom.GetPName[interval.name]
    totalTime = PulsesToMilliseconds[interval.totalTime]
    f.PutFL["%g.%g.  n: %g.  total: %g.  ",
LIST[ [cardinal[process]], [rope[name]], [integer[interval.starts]], [integer[totalTime]]]]
    avgTime = totalTime/interval.starts
    minTime = PulsesToMilliseconds[interval.minTime]
    maxTime = PulsesToMilliseconds[interval.maxTime]
    if interval.prematureStops > 0:
      f.PutFL["avg: %g.  range: [%g..%g], worst: %g, errs: %g",
LIST[ [integer[avgTime]], [integer[minTime]], [integer[maxTime]], [integer[interval.maxIndex]], [integer[interval.prematureStops]]] ]
    else:
      f.PutFL["avg: %g.  range: [%g..%g], worst: %g",
LIST[ [integer[avgTime]], [integer[minTime]], [integer[maxTime]], [integer[interval.maxIndex]]] ]
    if interval.starts > interval.stops:
f.PutF1[", %g extra starts", [integer[interval.starts - interval.stops]] ]
    f.PutRope["\n"]
    if children:
      for list: LIST OF IntervalInContext = interval.children, list.rest UNTIL list == None DO
        PrintIntervalInContext[f, process, list.first, nestingLevel+1, children]
        ENDLOOP
      }
    }
  }
  
def PrintInterval(f: IO.STREAM, intervalName, table, nestingLevel: NAT = 0):
  # Like PrintTable, but prints only that subset of the tree that contains the interval in question.
  if table # None:
    processCount = 0
    for lp: LIST OF ProcessPair = table.processes, lp.rest UNTIL lp == None DO
      pair: ProcessPair = lp.first
      for list: LIST OF IntervalInContext = pair.outer.children, list.rest UNTIL list == None DO
        PrintPartsContaining[f, processCount, intervalName, list.first, nestingLevel]
        ENDLOOP
      processCount = processCount + 1
      ENDLOOP
    }
  }
  
def PrintInt(f: IO.STREAM, intervalName, tableName, nestingLevel: NAT = 0):
  # Like PrintInterval but the table is specified by name.
  table = GetTable[tableName]
  if table # None: PrintInterval[f, intervalName, table, nestingLevel]
  }
  
PrintPartsContaining(f: IO.STREAM, process, intervalName, interval: IntervalInContext, nestingLevel: NAT = 0):
  if interval.name == intervalName: PrintIntervalInContext[f, process, interval, nestingLevel, TRUE]
  else: if ContainsNamedInterval[intervalName, interval]:
    PrintIntervalInContext[f, process, interval, nestingLevel, FALSE]
    for list: LIST OF IntervalInContext = interval.children, list.rest UNTIL list == None DO
      PrintPartsContaining[f, process, intervalName, list.first, nestingLevel + 1]
      ENDLOOP
    }
  }
  
def ContainsNamedInterval(intervalName, tree: IntervalInContext):
    # returns (BOOL):
  if tree.name == intervalName: return[TRUE]
  for list: LIST OF IntervalInContext = tree.children, list.rest UNTIL list == None DO
    if ContainsNamedInterval[intervalName, list.first]: return[TRUE]
    ENDLOOP
  return[FALSE]
  }
  
IntervalStatistics: TYPE == REF IntervalStatisticsObj
IntervalStatisticsObj: TYPE == CodeTimer.IntervalStatisticsObj

def GetIntervalTotals(intervalName, table):
    # returns (starts, totalMsec, averageMsec, minMsec, maxMsec, maxIndex, startsWithoutStops = 0):
  # Returns the total statistics for an interval (totaled over all of the contexts in which it was encountered).
  if table == None: return
  totalPulse = 0
  minPulse = 0x7FFFFFFF
  maxPulse = 0
  for list: LIST OF ProcessPair = table.processes, list.rest UNTIL list == None DO
    pair: ProcessPair = list.first
    [starts1, totalPulse1, minPulse1, maxPulse1, maxIndex1, prematureStops1] = NamedIntervalTotals[intervalName, pair.outer]
    if starts1 > 0:
      starts = starts + starts1
      totalPulse = totalPulse + totalPulse1
      if minPulse1 < minPulse: minPulse = minPulse1
      if maxPulse1 > maxPulse:
        maxPulse = maxPulse1
        maxIndex = maxIndex1
        }
      startsWithoutStops = startsWithoutStops + prematureStops1
      }
    ENDLOOP
  if starts == 0: return; # to avoid divide by 0 below
  totalMsec = PulsesToMilliseconds[totalPulse]
  averageMsec = totalMsec/starts
  minMsec = PulsesToMilliseconds[minPulse]
  maxMsec = PulsesToMilliseconds[maxPulse]
  }
  
def GetIntervalStats(intervalName, table):
    # returns (stats: LIST OF IntervalStatistics):
  # Returns the statistics individually for each context in which the interval was encountered.
  if table == None: return
  for lp: LIST OF ProcessPair = table.processes, lp.rest UNTIL lp == None DO
    pair: ProcessPair = lp.first
    theseStats: LIST OF IntervalStatistics = NamedIntervalStats[intervalName, pair.outer]
    stats = AppendStatList[theseStats, stats]
    ENDLOOP
  }
  
def NamedIntervalTotals(intervalName, interval: IntervalInContext):
    # returns (starts, totalPulse, minPulse, maxPulse, maxIndex, prematureStops):
  starts1, totalPulse1, minPulse1, maxPulse1, maxIndex1, prematureStops1
  starts = totalPulse = maxPulse = maxIndex = prematureStops = 0
  minPulse = 0x7FFFFFFF
  for list: LIST OF IntervalInContext = interval.children, list.rest UNTIL list == None DO
    [starts1, totalPulse1, minPulse1, maxPulse1, maxIndex1, prematureStops1] = NamedIntervalTotals[intervalName, list.first]
    if starts1 > 0:
      starts = starts + starts1
      totalPulse = totalPulse + totalPulse1
      if minPulse1 < minPulse: minPulse = minPulse1
      if maxPulse1 > maxPulse:
        maxPulse = maxPulse1
        maxIndex = maxIndex1
        }
      prematureStops = prematureStops + prematureStops1
      }
    ENDLOOP
  if interval.name == intervalName:
    if interval.starts > 0:
      starts = starts + interval.starts
      totalPulse = totalPulse + interval.totalTime
      if interval.minTime < minPulse: minPulse = interval.minTime
      if interval.maxTime > maxPulse:
        maxPulse = interval.maxTime
        maxIndex = interval.maxIndex
        }
      prematureStops = prematureStops + interval.prematureStops
      }
    }
  }
  # 
def AddAtom(entity: ATOM, entityList, ptr: LIST OF ATOM):
    # returns (newList, newPtr: LIST OF ATOM):
  if ptr == None:
    if not entityList == None: ERROR
    newPtr = newList = [entity]
    return
    }
  else:
    newList = entityList
    ptr.rest = [entity]
    newPtr = ptr.rest
    }
  }
  
def AddStats(entity: IntervalStatistics, entityList, ptr: LIST OF IntervalStatistics):
    # returns (newList, newPtr: LIST OF IntervalStatistics):
  if ptr == None:
    if not entityList == None: ERROR
    newPtr = newList = [entity]
    return
    }
  else:
    newList = entityList
    ptr.rest = [entity]
    newPtr = ptr.rest
    }
  }
  
def AppendStatList(list1, list2: LIST OF IntervalStatistics):
    # returns (result: LIST OF IntervalStatistics):
  pos: LIST OF IntervalStatistics
  newCell: LIST OF IntervalStatistics
  # Non-destructive (copies the first list).
  if list1 == None: return[list2]
  result = [list1.first]
  pos = result
  for l: LIST OF IntervalStatistics = list1.rest, l.rest UNTIL l == None DO
    newCell = [l.first]
    pos.rest = newCell
    pos = newCell
  ENDLOOP
  pos.rest  = list2
  };
  
def NamedIntervalStats(intervalName, interval: IntervalInContext):
    # returns (stats: LIST OF IntervalStatistics):
  statTail, childStats: LIST OF IntervalStatistics
  if interval.name == intervalName:
    if interval.starts > 0:
      tail: LIST OF ATOM
      parent = IntervalInContext()
      theseStats: IntervalStatistics
      theseStats = NEW[CodeTimer.IntervalStatisticsObj]
      theseStats.process = 0; # for now
      parent = interval.parent
      UNTIL parent.parent == None DO
        [theseStats.context, tail] = AddAtom[parent.name, theseStats.context, tail]
        parent = parent.parent
        ENDLOOP
      theseStats.starts = interval.starts
      theseStats.totalMsec = PulsesToMilliseconds[interval.totalTime]
      theseStats.minMsec = PulsesToMilliseconds[interval.minTime]
      theseStats.maxMsec = PulsesToMilliseconds[interval.maxTime]
      theseStats.maxIndex = interval.maxIndex
      theseStats.startsWithoutStops = interval.prematureStops
      [stats, statTail] = AddStats[theseStats, stats, statTail]
      }
    }
  for list: LIST OF IntervalInContext = interval.children, list.rest UNTIL list == None DO
    childStats = NamedIntervalStats[intervalName, list.first]
    stats = AppendStatList[stats, childStats]
    ENDLOOP
  }
  # 
"""

def CodeTimerNoteThreadsOn():
  noteThreads = 1
  
def CodeTimerNoteThreadsOff():
  noteThreads = 0
  
def CodeTimerOn():
  c = static._get('c')
  c.codeTimerOn = 1
  
def CodeTimerOff():
  c = static._get('c')
  c.codeTimerOn = 0
  
def TimerOn():
  c = static._get('c')
  c.codeTimerOn = 1
  
def TimerOff():
  c = static._get('c')
  c.codeTimerOn = 0

"""  
# The routines below were registered shell commands in Cedar.
def PrintCodeTimes():
  nameStream: IO.STREAM = IO.RIS[cmd.commandLine]
  name: Rope.ROPE
  atom: ATOM
  table
  if cmd.commandLine == "": return[$Failure, "Please specify a table name"]
  [] = IO.SkipWhitespace[nameStream]
  name = IO.GetLineRope[nameStream]
  atom = Atom.MakeAtom[name]
  table = GetTable[atom]
  if table # None: PrintTable[cmd.out, table]
  else: cmd.out.PutRope["No such table.\n"]
  }
  
def ResetCodeTimes():
  nameStream: IO.STREAM = IO.RIS[cmd.commandLine]
  name: Rope.ROPE
  atom: ATOM
  table
  if cmd.commandLine == "": return[$Failure, "Please specify a table name"]
  [] = IO.SkipWhitespace[nameStream]
  name = IO.GetLineRope[nameStream]
  atom = Atom.MakeAtom[name]
  table = GetTable[atom]
  if table # None: ResetTable[table]
else: cmd.out.PutF1["I don't (yet) know of a table named %g.\n", [atom[atom]]]
  }
  
def PrintIntervalTimes():
  nameStream: IO.STREAM = IO.RIS[cmd.commandLine]
  name: Rope.ROPE
  tableName, intervalName
  table
  if cmd.commandLine == "": return[$Failure, "Please specify a table name"]
  [] = IO.SkipWhitespace[nameStream]
  name = IO.GetTokenRope[nameStream].token
  intervalName = Atom.MakeAtom[name]
  name = IO.GetTokenRope[nameStream].token
  tableName = Atom.MakeAtom[name]
  table = GetTable[tableName]
  if table # None: PrintInterval[cmd.out, intervalName, table]
else: cmd.out.PutF1["I don't (yet) know of a table named %g.\n", [atom[tableName]]]
  }
  
def PrintIntervalTotals():
  nameStream: IO.STREAM = IO.RIS[cmd.commandLine]
  tableRope, intervalRope: Rope.ROPE
  tableName, intervalName
  table
  if cmd.commandLine == "": return[$Failure, "Please specify a table name"]
  [] = IO.SkipWhitespace[nameStream]
  intervalRope = IO.GetTokenRope[nameStream].token
  intervalName = Atom.MakeAtom[intervalRope]
  tableRope = IO.GetTokenRope[nameStream].token
  tableName = Atom.MakeAtom[tableRope]
  table = GetTable[tableName]
  if table # None:
    [starts, totalMsec, averageMsec, minMsec, maxMsec, maxIndex, prematureStops] = GetIntervalTotals[intervalName, table]
    cmd.out.PutF["%g.  n: %g.  total: %g.  ", [rope[intervalRope]], [integer[starts]], [integer[totalMsec]]]
    if prematureStops > 0:
      cmd.out.PutFL["avg: %g.  range: [%g..%g], worst: %g, errs: %g\n",
LIST[ [integer[averageMsec]], [integer[minMsec]], [integer[maxMsec]], [integer[maxIndex]], [integer[prematureStops]]] ]
    else:
      cmd.out.PutFL["avg: %g.  range: [%g..%g], worst: %g\n",
LIST[ [integer[averageMsec]], [integer[minMsec]], [integer[maxMsec]], [integer[maxIndex]]] ]
    }
    else: cmd.out.PutF1["I don't (yet) know of a table named %g.\n", [atom[tableName]]]
  }
  
def ResetIntervalTimes():
  nameStream: IO.STREAM = IO.RIS[cmd.commandLine]
  name: Rope.ROPE
  tableName, intervalName
  table
  if cmd.commandLine == "": return[$Failure, "Please specify a table name"]
  [] = IO.SkipWhitespace[nameStream]
  name = IO.GetTokenRope[nameStream].token
  intervalName = Atom.MakeAtom[name]
  name = IO.GetTokenRope[nameStream].token
  tableName = Atom.MakeAtom[name]
  table = GetTable[tableName]
  if table # None: ResetInterval[intervalName, table]
else: cmd.out.PutF1["I don't (yet) know of a table named %g.\n", [atom[tableName]]]
  }
  
def PrintCodeTimeTables():
  PrintTableName: CodeTimer.ForEachTableProc == {
    # PROC [tableName, table)
    # returns (done: BOOL _ FALSE]
    cmd.out.PutF1["\n   %g", [atom[tableName]] ]
    }
  [] = ForEachTable[PrintTableName]
  cmd.out.PutRope["\n"]
  }
"""

# Command Registration
# 
def Init():
  global defaultProcess
  defaultProcess = thread.get_ident()
  c = static._get('c')
  c.TablesRef = {}
  c.intervalPool = [None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None] # A maximum of 25 IntervalInContext's
  c.intervalPoolMax = 25
  c.intervalPoolIndex = -1
  
  
"""
  Commander.Register["PrintCodeTimes", PrintCodeTimes, "PrintCodeTimes <tablename> # prints out the minimum, maximum, and average times taken to execute the marked code blocks in the table named in the first argument"]
  Commander.Register["ResetCodeTimes", ResetCodeTimes, "ResetCodeTimes <tablename> # zeros the code times for all of the intervals in this table"]
  Commander.Register["PrintCodeTimeTables", PrintCodeTimeTables, "Prints out all code time tables that CodeTimer currently knows about"]
  Commander.Register["PrintIntervalTimes", PrintIntervalTimes, "PrintIntervalTime <intervalname> <tablename> # prints out the minimum, maximum, and average times taken to execute the named interval (in each context in which in appears) and its children"]
  Commander.Register["PrintIntervalTotals", PrintIntervalTotals, "PrintIntervalTotals <intervalname> <tablename> # prints out the minimum, maximum, and average times taken to execute the named interval (totaled over all contexts in which it appears)"]
  Commander.Register["ResetIntervalTimes", ResetIntervalTimes, "ResetIntervalTimes <intervalname> <tablename> # zeros the code times for the named interval in the named table"]
  Commander.Register["codeTimerOn", CodeTimerOn, "Causes CodeTimer to begin timing code intervals that have been marked with StartInt and StopInt calls (use CodeTimerTool to view the results)"]
  Commander.Register["codeTimerOff", CodeTimerOff, "Causes CodeTimer to stop timing code intervals that have been marked with StartInt and StopInt calls (use CodeTimerTool to view the results)"]
  Commander.Register["codeTimerNoteThreadsOn", CodeTimerNoteThreadsOn, "Causes CodeTimer to distinguish calls to the same interval by different threads"]
  Commander.Register["codeTimerNoteThreadsOff", CodeTimerNoteThreadsOff, "Causes CodeTimer to treat calls to an interval identically regardless of which thread makes the call (this is the default)"]
"""

def Test_Inner(n):
    StartInt('InnermostBlock', 'CodeTimer')
    time.sleep(n)
    StopInt('InnermostBlock', 'CodeTimer')

def Test():
  CodeTimerOn()
  for i in range(3):
    StartInt('LoopOnI', 'CodeTimer')
    time.sleep(1)
    
    StartInt('InnerBlock', 'CodeTimer')
    time.sleep(1)
    Test_Inner(1)
    StopInt('InnerBlock', 'CodeTimer')
    
    StartInt('AnotherBlock', 'CodeTimer')
    Test_Inner(2)
    StopInt('AnotherBlock', 'CodeTimer')
    
    StopInt('LoopOnI', 'CodeTimer')
    
  PrintTable(sys.stdout, 'CodeTimer')
  
Init()
  




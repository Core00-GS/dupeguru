# Created On: 2011-11-27
# Copyright 2012 Hardcoded Software (http://www.hardcoded.net)
# 
# This software is licensed under the "BSD" License as described in the "LICENSE" file, 
# which should be included with this package. The terms are also available at 
# http://www.hardcoded.net/licenses/bsd_license

from qtlib.column import Column
from ..base.results_model import ResultsModel as ResultsModelBase
from core_me.result_table import ResultTable

# Little hack to remove the 'marked' column which isn't there in the Qt GUI.
del ResultTable.COLUMNS[0]

class ResultsModel(ResultsModelBase):
    COLUMNS = [
        Column('name', defaultWidth=200),
        Column('folder_path', defaultWidth=180),
        Column('size', defaultWidth=60),
        Column('duration', defaultWidth=60),
        Column('bitrate', defaultWidth=50),
        Column('samplerate', defaultWidth=60),
        Column('extension', defaultWidth=40),
        Column('mtime', defaultWidth=120),
        Column('title', defaultWidth=120),
        Column('artist', defaultWidth=120),
        Column('album', defaultWidth=120),
        Column('genre', defaultWidth=80),
        Column('year', defaultWidth=40),
        Column('track', defaultWidth=40),
        Column('comment', defaultWidth=120),
        Column('percentage', defaultWidth=60),
        Column('words', defaultWidth=120),
        Column('dupe_count', defaultWidth=80),
    ]
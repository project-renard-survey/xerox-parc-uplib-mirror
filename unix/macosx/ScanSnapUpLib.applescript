-- For Fujitsu ScanSnap S500M scanner
--
-- when file dropped on script, send it to UpLib
--
-- This file is part of the "UpLib 1.7.11" release.
-- Copyright (C) 2003-2011  Palo Alto Research Center, Inc.
-- 
-- This program is free software; you can redistribute it and/or modify
-- it under the terms of the GNU General Public License as published by
-- the Free Software Foundation; either version 2 of the License, or
-- (at your option) any later version.
-- 
-- This program is distributed in the hope that it will be useful,
-- but WITHOUT ANY WARRANTY; without even the implied warranty of
-- MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
-- GNU General Public License for more details.
-- 
-- You should have received a copy of the GNU General Public License along
-- with this program; if not, write to the Free Software Foundation, Inc.,
-- 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
--
-- To use this, compile it into an application, and tell the ScanSnap
-- Manager to use it for fresh scans
--

property prog : "/Library/PDF Services/Save PDF to UpLib"

on run
	display dialog prog
	display dialog quoted form of prog
end run

on open target_files
	set programPath to quoted form of prog
	repeat with n_file in target_files
		set filePath to quoted form of POSIX path of n_file
		try
			do shell script programPath & " ScanSnap ScanSnap " & filePath
		end try
	end repeat
end open

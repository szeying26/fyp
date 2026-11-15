Attribute VB_Name = "DailySolverV2"
Option Explicit

' Solves the "Jobs" sheet with Excel Solver, using the same model and options as
' "Copy ver MV model.xlsx", in the same order as that workbook:
'
'   Stage 1  minimise risk (lambda = 1) for K = 4..12, historical average returns.
'            The best cardinality is the K with the highest cumulative return when
'            the portfolio is held through 2025 (sheet "Stage 1 best K").
'   Stage 2  risk-return trade-off at the best K from stage 1, for each lambda:
'            static (historical average returns) and daily (that day's predictions).
'   Stage 3  sensitivity check: daily trade-off at lambda = 0.9 for every other K.
'
' Every portfolio is backtested over the whole of 2025. If the "Predicted data" sheet
' does not cover every trading day of 2025 (an older copy of this workbook starts on
' 3 Feb), the missing days are added at the bottom of that sheet and the jobs for
' them at the bottom of the "Jobs" sheet; finished jobs are kept.
'
' Needs the module Data2025 (file Data2025.bas) and the Solver reference:
' Tools > References... > tick "Solver".
' Rows that already have a Solver result code are skipped, so the macro can be
' stopped and run again; it continues with the unsolved jobs.

Private Const FIRST_JOB_ROW As Long = 2
Private Const COL_MODE As Long = 2      ' B: "minrisk" or "tradeoff"
Private Const COL_K As Long = 3         ' C
Private Const COL_LAMBDA As Long = 4    ' D
Private Const COL_DAY As Long = 5       ' E: 0 = historical average, 1..n = row of "Predicted data"
Private Const COL_DATE As Long = 6      ' F
Private Const COL_W1 As Long = 7        ' G..R: the 12 weights
Private Const COL_OBJ As Long = 19      ' S
Private Const COL_CODE As Long = 20     ' T
Private Const COL_SECS As Long = 21     ' U
Private Const COL_RET As Long = 22      ' V
Private Const COL_VAR As Long = 23      ' W
Private Const COL_SUM As Long = 24      ' X
Private Const COL_HELD As Long = 25     ' Y
Private Const SAVE_EVERY As Long = 100  ' save the workbook after this many solved jobs
Private Const MAX_SECONDS As Long = 100 ' time limit per job
Private Const SENS_LAMBDA As Double = 0.9   ' lambda of the stage 3 sensitivity check
Private Const SLOW_LAMBDA As Double = 0.97  ' daily jobs with lambda >= this are slow and are solved last
Private Const SHEET_ACTUAL As String = "Actual 2025"
Private Const SHEET_STAGE1 As String = "Stage 1 best K"

' Stage 1 only: solves the minimise-risk jobs (if not solved yet), builds the
' "Stage 1 best K" sheet and reports the best cardinality at lambda = 1.
Sub RunStage1BestCardinality()
    Dim bestK As Long
    SolveJobs 1, 0
    bestK = BuildStage1()
    SaveQuietly
    MsgBox "Best cardinality at lambda = 1: K = " & bestK & vbCrLf & "See the sheet '" & SHEET_STAGE1 & "'."
End Sub

' Everything: stage 1, then stage 2 at the best K from stage 1, then stage 3.
Sub RunAllStages()
    Dim bestK As Long, n As Long
    SolveJobs 1, 0
    bestK = BuildStage1()
    EnsurePredictions
    EnsureJobs bestK
    SaveQuietly
    n = SolveJobs(2, bestK)         ' all needed jobs except the slow daily ones
    n = n + SolveJobs(3, bestK)     ' the slow daily jobs (lambda >= 0.97)
    SaveQuietly
    Worksheets(SHEET_STAGE1).Activate
    MsgBox "Finished. Best cardinality at lambda = 1: K = " & bestK & ". Jobs solved in this run: " & n & "." & vbCrLf & "Please save the workbook."
End Sub

' Is the job on this row part of the given phase?
'   phase 1: minimise-risk jobs
'   phase 2: trade-off jobs at the best K, and the lambda = 0.9 daily jobs for the other K, except slow daily jobs
'   phase 3: the same set, including the slow daily jobs
Private Function Wanted(ByVal wsJ As Worksheet, ByVal r As Long, ByVal phase As Long, ByVal bestK As Long) As Boolean
    Dim mode As String, k As Long, lam As Double, d As Long, needed As Boolean
    mode = LCase(Trim(CStr(wsJ.Cells(r, COL_MODE).Value)))
    If phase = 1 Then
        Wanted = (mode = "minrisk")
        Exit Function
    End If
    If mode <> "tradeoff" Then
        Wanted = False
        Exit Function
    End If
    k = CLng(wsJ.Cells(r, COL_K).Value)
    lam = CDbl(wsJ.Cells(r, COL_LAMBDA).Value)
    d = CLng(wsJ.Cells(r, COL_DAY).Value)
    needed = (k = bestK) Or (d > 0 And Abs(lam - SENS_LAMBDA) < 0.0001)
    If phase = 2 And d > 0 And lam >= SLOW_LAMBDA - 0.0001 Then needed = False
    Wanted = needed
End Function

' Solves every unsolved job of the phase. Returns the number of jobs solved.
Private Function SolveJobs(ByVal phase As Long, ByVal bestK As Long) As Long
    Dim wsM As Worksheet, wsJ As Worksheet, wsP As Worksheet, wsC As Worksheet
    Dim r As Long, lastRow As Long, i As Long, d As Long
    Dim mode As String, code As Variant, t0 As Double
    Dim solved As Long, total As Long, todo As Long

    Set wsM = ThisWorkbook.Worksheets("Solver model")
    Set wsJ = ThisWorkbook.Worksheets("Jobs")
    Set wsP = ThisWorkbook.Worksheets("Predicted data")
    Set wsC = ThisWorkbook.Worksheets("Covariance")

    lastRow = wsJ.Cells(wsJ.Rows.Count, 1).End(xlUp).Row
    total = lastRow - FIRST_JOB_ROW + 1
    For r = FIRST_JOB_ROW To lastRow
        If IsEmpty(wsJ.Cells(r, COL_CODE).Value) Then
            If Wanted(wsJ, r, phase, bestK) Then todo = todo + 1
        End If
    Next r
    SolveJobs = 0
    If todo = 0 Then Exit Function

    wsM.Activate
    Application.ScreenUpdating = False

    For r = FIRST_JOB_ROW To lastRow
        If IsEmpty(wsJ.Cells(r, COL_CODE).Value) Then
            If Wanted(wsJ, r, phase, bestK) Then
                mode = LCase(Trim(CStr(wsJ.Cells(r, COL_MODE).Value)))
                d = CLng(wsJ.Cells(r, COL_DAY).Value)

                ' inputs: K, lambda, expected returns
                wsM.Range("B3").Value = wsJ.Cells(r, COL_K).Value
                wsM.Range("B4").Value = wsJ.Cells(r, COL_LAMBDA).Value
                For i = 1 To 12
                    If d = 0 Then
                        wsM.Cells(10 + i, 2).Value = wsC.Cells(3 + i, 2).Value        ' historical average
                    Else
                        wsM.Cells(10 + i, 2).Value = wsP.Cells(1 + d, 1 + i).Value    ' that day's prediction
                    End If
                    ' starting point: equal weights, every stock selected
                    wsM.Cells(10 + i, 3).Value = 1 / 12
                    wsM.Cells(10 + i, 4).Value = 1
                Next i
                Application.Calculate

                ' the Solver model, as in the original workbook
                SolverReset
                SolverOptions MaxTime:=MAX_SECONDS, Iterations:=2147483647, Precision:=0.000001, _
                    AssumeLinear:=False, StepThru:=False, Estimates:=1, Derivatives:=2, SearchOption:=1, _
                    IntTolerance:=0, Scaling:=False, Convergence:=0.0001, AssumeNonNeg:=True, _
                    PopulationSize:=100, RandomSeed:=0, MultiStart:=False, RequireBounds:=True, _
                    MutationRate:=0.1, MaxSubproblems:=2147483647, MaxIntegerSols:=2147483647, _
                    SolveWithout:=False, MaxTimeNoImp:=60
                If mode = "minrisk" Then
                    SolverOk SetCell:="$B$26", MaxMinVal:=2, ValueOf:=0, ByChange:="$C$11:$D$22", Engine:=1
                Else
                    SolverOk SetCell:="$B$27", MaxMinVal:=1, ValueOf:=0, ByChange:="$C$11:$D$22", Engine:=1
                End If
                SolverAdd CellRef:="$C$23", Relation:=2, FormulaText:="1"            ' weights sum to 1
                SolverAdd CellRef:="$D$11:$D$22", Relation:=5, FormulaText:="binary" ' selection cells are 0 or 1
                SolverAdd CellRef:="$D$23", Relation:=2, FormulaText:="$B$3"         ' exactly K stocks
                SolverAdd CellRef:="$E$11:$E$22", Relation:=1, FormulaText:="0"      ' weight <= max x binary
                SolverAdd CellRef:="$F$11:$F$22", Relation:=1, FormulaText:="0"      ' weight >= min x binary
                If mode = "minrisk" Then
                    SolverAdd CellRef:="$B$25", Relation:=3, FormulaText:="$B$7"     ' return floor
                End If

                t0 = Timer
                code = SolverSolve(UserFinish:=True)
                SolverFinish KeepFinal:=1

                ' results
                For i = 1 To 12
                    wsJ.Cells(r, COL_W1 + i - 1).Value = wsM.Cells(10 + i, 3).Value
                Next i
                If mode = "minrisk" Then
                    wsJ.Cells(r, COL_OBJ).Value = wsM.Range("B26").Value
                Else
                    wsJ.Cells(r, COL_OBJ).Value = wsM.Range("B27").Value
                End If
                wsJ.Cells(r, COL_SECS).Value = Round(Timer - t0, 2)
                wsJ.Cells(r, COL_RET).Value = wsM.Range("B25").Value
                wsJ.Cells(r, COL_VAR).Value = wsM.Range("B26").Value
                wsJ.Cells(r, COL_SUM).Value = wsM.Range("C23").Value
                wsJ.Cells(r, COL_HELD).Value = wsM.Range("D23").Value
                wsJ.Cells(r, COL_CODE).Value = code    ' written last: marks the job as done

                solved = solved + 1
                Application.StatusBar = "Solver, phase " & phase & ": " & solved & " of " & todo & " jobs solved in this run (job " & (r - FIRST_JOB_ROW + 1) & " of " & total & ")"
                DoEvents
                If solved Mod SAVE_EVERY = 0 Then SaveQuietly
            End If
        End If
    Next r

    Application.ScreenUpdating = True
    Application.StatusBar = False
    SolveJobs = solved
End Function

Private Sub SaveQuietly()
    On Error Resume Next
    Application.DisplayAlerts = False
    ThisWorkbook.Save
    Application.DisplayAlerts = True
    On Error GoTo 0
End Sub

Private Function SheetExists(ByVal sheetName As String) As Boolean
    Dim ws As Worksheet
    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(sheetName)
    On Error GoTo 0
    SheetExists = Not ws Is Nothing
End Function

' Returns the sheet with that name, emptied; creates it at the end if it does not exist.
Private Function FreshSheet(ByVal sheetName As String) As Worksheet
    Dim ws As Worksheet
    If SheetExists(sheetName) Then
        Set ws = ThisWorkbook.Worksheets(sheetName)
        ws.Cells.Clear
    Else
        Set ws = ThisWorkbook.Worksheets.Add(After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count))
        ws.Name = sheetName
    End If
    Set FreshSheet = ws
End Function

' Builds "Actual 2025" (actual daily returns and the daily return of each stage 1
' portfolio) and "Stage 1 best K" (the 2025 backtest of each K). Returns the best K.
Private Function BuildStage1() As Long
    Dim wsJ As Worksheet, wsA As Worksheet, wsS As Worksheet
    Dim a() As String, parts() As String, vals() As String, arr() As Variant
    Dim nDays As Long, i As Long, j As Long, r As Long, lastRow As Long
    Dim n As Long, jobRow(1 To 50) As Long, colL As String, lastA As Long
    Dim stockNames As Variant, h As Variant, sRow As Long, f1 As Long, f2 As Long

    Set wsJ = ThisWorkbook.Worksheets("Jobs")
    Application.ScreenUpdating = False

    ' the minimise-risk jobs, in sheet order
    lastRow = wsJ.Cells(wsJ.Rows.Count, 1).End(xlUp).Row
    For r = FIRST_JOB_ROW To lastRow
        If LCase(Trim(CStr(wsJ.Cells(r, COL_MODE).Value))) = "minrisk" And n < 50 Then
            n = n + 1
            jobRow(n) = r
        End If
    Next r

    ' actual 2025 returns
    Data2025.LoadActual a
    nDays = UBound(a)
    ReDim arr(1 To nDays, 1 To 13)
    For i = 1 To nDays
        parts = Split(a(i), "|")
        vals = Split(parts(1), ",")
        arr(i, 1) = parts(0)
        For j = 0 To 11
            arr(i, j + 2) = Val(vals(j))
        Next j
    Next i
    Set wsA = FreshSheet(SHEET_ACTUAL)
    stockNames = Array("CIMB", "MAYBANK", "PUBLIC BANK", "TELEKOM", "PETRONAS", "SUNWAY", "IHH HEALTHCARE", "TNB", _
                  "HONG LEONG BANK", "MAXIS", "AXIATA", "PRESS METAL")
    wsA.Cells(1, 1).Value = "Date"
    For j = 0 To 11
        wsA.Cells(1, j + 2).Value = stockNames(j)
    Next j
    wsA.Range("A2:A" & (nDays + 1)).NumberFormat = "@"
    wsA.Range(wsA.Cells(2, 1), wsA.Cells(nDays + 1, 13)).Value = arr
    lastA = nDays + 1
    ' daily return of each stage 1 portfolio: weights (Jobs sheet) x actual returns
    For i = 1 To n
        wsA.Cells(1, 14 + i).Value = "Min risk K=" & wsJ.Cells(jobRow(i), COL_K).Value & ": portfolio return"
        wsA.Range(wsA.Cells(2, 14 + i), wsA.Cells(lastA, 14 + i)).Formula = _
            "=SUMPRODUCT($B2:$M2,Jobs!$G$" & jobRow(i) & ":$R$" & jobRow(i) & ")"
    Next i
    wsA.Range(wsA.Cells(2, 2), wsA.Cells(lastA, 14 + n)).NumberFormat = "0.0000%"
    wsA.Rows(1).Font.Bold = True
    wsA.Cells(1, 16 + n).Value = "Actual daily log returns, 2025. Source: DATASET/test_log_returns.csv. Portfolio return = weights x returns, as in the original workbook."

    ' stage 1 table
    Set wsS = FreshSheet(SHEET_STAGE1)
    wsS.Range("A1").Value = "Stage 1: best cardinality at lambda = 1 (minimise risk, Excel Solver)"
    wsS.Range("A1").Font.Bold = True
    wsS.Range("A1").Font.Size = 14
    h = Array("K", "Row on Jobs sheet", "Solver result code", "Portfolio variance", "Expected daily return", _
              "Cumulative return, all 2025 (" & arr(1, 1) & " to " & arr(nDays, 1) & ", " & nDays & " days)", _
              "Best K")
    For j = 0 To 6
        wsS.Cells(3, j + 1).Value = h(j)
    Next j
    wsS.Rows(3).Font.Bold = True
    wsS.Rows(3).WrapText = True
    f1 = 4
    f2 = 3 + n
    For i = 1 To n
        sRow = 3 + i
        colL = Split(wsA.Cells(1, 14 + i).Address(True, False), "$")(0)
        wsS.Cells(sRow, 1).Formula = "=Jobs!C" & jobRow(i)
        wsS.Cells(sRow, 2).Value = jobRow(i)
        wsS.Cells(sRow, 3).Formula = "=Jobs!T" & jobRow(i)
        wsS.Cells(sRow, 4).Formula = "=Jobs!W" & jobRow(i)
        wsS.Cells(sRow, 5).Formula = "=Jobs!V" & jobRow(i)
        wsS.Cells(sRow, 6).Formula = "=EXP(SUMPRODUCT(LN(1+'" & SHEET_ACTUAL & "'!" & colL & "2:" & colL & lastA & ")))-1"
        wsS.Cells(sRow, 7).Formula = "=IF(F" & sRow & "=MAX($F$" & f1 & ":$F$" & f2 & "),""best"","""")"
    Next i
    wsS.Range("D" & f1 & ":D" & f2).NumberFormat = "0.00000000"
    wsS.Range("E" & f1 & ":E" & f2).NumberFormat = "0.0000%"
    wsS.Range("F" & f1 & ":F" & f2).NumberFormat = "0.00%"
    sRow = f2 + 2
    wsS.Cells(sRow, 1).Value = "Best cardinality at lambda = 1 (highest cumulative return, all 2025). Used for stage 2."
    wsS.Cells(sRow, 6).Formula = "=INDEX(A" & f1 & ":A" & f2 & ",MATCH(MAX(F" & f1 & ":F" & f2 & "),F" & f1 & ":F" & f2 & ",0))"
    wsS.Range(wsS.Cells(sRow, 1), wsS.Cells(sRow, 6)).Font.Bold = True
    wsS.Cells(sRow + 2, 1).Value = "Method: each K's minimum-variance portfolio (historical average returns, 2022-2024 covariance) is held with fixed weights through 2025, as in 'Copy ver MV model.xlsx'."
    wsS.Cells(sRow + 3, 1).Value = "Note: the best K is chosen with actual 2025 returns, the same year the strategy is tested on. This follows the original workbook; it is a look-ahead choice."
    wsS.Columns("A:G").ColumnWidth = 22

    Application.Calculate
    BuildStage1 = CLng(wsS.Cells(sRow, 6).Value)
    Application.ScreenUpdating = True
End Function

' Makes the "Predicted data" sheet cover every day in the Data2025 module: days that
' are not on the sheet yet are added at the bottom. Existing rows are not moved, so the
' day numbers of finished jobs stay valid.
Private Sub EnsurePredictions()
    Dim wsP As Worksheet, p() As String, parts() As String, vals() As String
    Dim lastRow As Long, n As Long, i As Long, j As Long, r As Long, found As Boolean, v As Variant

    Set wsP = ThisWorkbook.Worksheets("Predicted data")
    lastRow = wsP.Cells(wsP.Rows.Count, 1).End(xlUp).Row
    v = wsP.Range("A1:A" & lastRow).Value
    Data2025.LoadPredicted p
    n = lastRow
    For i = 1 To UBound(p)
        parts = Split(p(i), "|")
        found = False
        For r = 2 To lastRow
            If Left(CStr(v(r, 1)), 10) = Left(parts(0), 10) Then
                found = True
                Exit For
            End If
        Next r
        If Not found Then
            n = n + 1
            vals = Split(parts(1), ",")
            wsP.Cells(n, 1).NumberFormat = "@"
            wsP.Cells(n, 1).Value = parts(0)
            For j = 0 To 11
                wsP.Cells(n, j + 2).Value = Val(vals(j))
                wsP.Cells(n, j + 2).NumberFormat = "0.0000%"
            Next j
        End If
    Next i
End Sub

' Makes sure the Jobs sheet lists every job that is needed, adding the missing ones at the bottom:
'   static trade-off at the best K for each lambda,
'   daily trade-off at the best K for each lambda below 1, for every row of "Predicted data",
'   daily trade-off at lambda = 0.9 for every other K, for every row of "Predicted data".
Private Sub EnsureJobs(ByVal bestK As Long)
    Dim wsJ As Worksheet, wsP As Worksheet, lams As Variant, v As Variant
    Dim r As Long, lastRow As Long, nPred As Long, li As Long, d As Long, k As Long, i As Long
    Dim seenStatic(0 To 8) As Boolean, seen() As Boolean, lam As Double, need As Boolean

    Set wsJ = ThisWorkbook.Worksheets("Jobs")
    Set wsP = ThisWorkbook.Worksheets("Predicted data")
    lams = Array(0.1, 0.3, 0.5, 0.7, 0.9, 0.95, 0.97, 0.99, 1)
    nPred = wsP.Cells(wsP.Rows.Count, 1).End(xlUp).Row - 1
    ReDim seen(4 To 12, 0 To 8, 1 To nPred)

    ' which jobs are already listed
    lastRow = wsJ.Cells(wsJ.Rows.Count, 1).End(xlUp).Row
    v = wsJ.Range("A1:E" & lastRow).Value
    For r = FIRST_JOB_ROW To lastRow
        If LCase(Trim(CStr(v(r, COL_MODE)))) = "tradeoff" Then
            k = CLng(v(r, COL_K))
            d = CLng(v(r, COL_DAY))
            li = -1
            For i = 0 To 8
                If Abs(CDbl(v(r, COL_LAMBDA)) - CDbl(lams(i))) < 0.0001 Then li = i
            Next i
            If li >= 0 And k >= 4 And k <= 12 Then
                If d = 0 Then
                    If k = bestK Then seenStatic(li) = True
                ElseIf d <= nPred Then
                    seen(k, li, d) = True
                End If
            End If
        End If
    Next r

    ' add what is missing
    r = lastRow
    For li = 0 To 8
        If Not seenStatic(li) Then
            r = r + 1
            AddJob wsJ, r, bestK, CDbl(lams(li)), 0, "static"
        End If
    Next li
    For k = 4 To 12
        For li = 0 To 8
            lam = CDbl(lams(li))
            If k = bestK Then
                need = (lam < 0.9999)
            Else
                need = (Abs(lam - SENS_LAMBDA) < 0.0001)
            End If
            If need Then
                For d = 1 To nPred
                    If Not seen(k, li, d) Then
                        r = r + 1
                        AddJob wsJ, r, k, lam, d, wsP.Cells(1 + d, 1).Value
                    End If
                Next d
            End If
        Next li
    Next k
End Sub

Private Sub AddJob(ByVal wsJ As Worksheet, ByVal r As Long, ByVal k As Long, ByVal lam As Double, ByVal d As Long, ByVal dateText As Variant)
    wsJ.Cells(r, 1).Value = r - FIRST_JOB_ROW + 1
    wsJ.Cells(r, COL_MODE).Value = "tradeoff"
    wsJ.Cells(r, COL_K).Value = k
    wsJ.Cells(r, COL_LAMBDA).Value = lam
    wsJ.Cells(r, COL_DAY).Value = d
    wsJ.Cells(r, COL_DATE).NumberFormat = "@"
    wsJ.Cells(r, COL_DATE).Value = dateText
End Sub

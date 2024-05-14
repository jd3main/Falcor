$Env:FALCOR_DEVMODE = 1

# $BinPath = "..\..\..\build\windows-ninja-msvc-d3d12\bin\Debug\"
$BinPath = "..\..\..\build\windows-ninja-msvc-d3d12\bin\Release\"

$ScriptPath = "..\..\..\Source\Mogwai\Data\DynamicWeightingSVGF_exp_fovea.py"

$MogwaiPath = $BinPath+"Mogwai.exe"


$Command = $MogwaiPath+" --script "+$scriptPath+$scriptName+" --precise --deferred "+$args
Write-Output $Command
Invoke-Expression -Command $Command


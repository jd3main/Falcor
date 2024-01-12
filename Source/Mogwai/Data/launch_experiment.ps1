$Env:FALCOR_DEVMODE = 1
$BinPath = "..\..\..\build\windows-ninja-msvc-d3d12\bin\Debug\"
$ScriptPath = "..\..\..\Source\Mogwai\Data\DynamicWeightingSVGF_experiment.py"
# $ScenePath = "..\..\..\..\Scenes\VeachAjar\VeachAjarAnimated.pyscene"

$MogwaiPath = $BinPath+"Mogwai.exe"

# $Command = $MogwaiPath+" --script "+$scriptPath+$scriptName+" --deferred --scene "+$ScenePath
$Command = $MogwaiPath+" --script "+$scriptPath+$scriptName
Echo $Command
Invoke-Expression -Command $Command


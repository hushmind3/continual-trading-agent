param([Parameter(Mandatory)][string]$ScriptPath)
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
$tokens=$null; $parseErrors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($ScriptPath,[ref]$tokens,[ref]$parseErrors)
if($parseErrors.Count){throw ($parseErrors.Message -join '; ')}
$parameters=@(foreach($p in $ast.ParamBlock.Parameters){
 $required=$false; $choices=@(); $default=$null
 foreach($a in $p.Attributes){
  if($a.TypeName.Name -eq 'Parameter'){
   foreach($n in $a.NamedArguments){if($n.ArgumentName -eq 'Mandatory'){$required=$n.ExpressionOmitted -or [bool]$n.Argument.SafeGetValue()}}
  }
  if($a.TypeName.Name -eq 'ValidateSet'){$choices=@($a.PositionalArguments | ForEach-Object {$_.SafeGetValue()})}
 }
 if($p.DefaultValue){try{$default=$p.DefaultValue.SafeGetValue()}catch{throw "Unsupported dynamic default: $($p.Name.VariablePath.UserPath)"}}
 $type=$p.StaticType.Name
 if($type -notin @('String','SwitchParameter','Int32','Int64','Double','Object')){throw "Unsupported parameter type: $type"}
 [ordered]@{name=$p.Name.VariablePath.UserPath;kind=$(if($type -eq 'SwitchParameter'){'switch'}elseif($type -in @('Int32','Int64','Double')){'number'}else{'text'});required=$required;choices=$choices;default=$default}
})
$help=$ast.GetHelpContent()
[ordered]@{parameters=$parameters;synopsis=$help.Synopsis;description=$help.Description;syntax_checked=$true} | ConvertTo-Json -Depth 8 -Compress

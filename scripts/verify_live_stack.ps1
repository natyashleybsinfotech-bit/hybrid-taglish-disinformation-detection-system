param(
    [string]$ApiBase = 'http://127.0.0.1:8000',
    [string]$DashboardUrl = 'http://127.0.0.1:5173',
    [int]$ShortRequests = 10
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Net.Http
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

function Get-ListenerPid([int]$Port) {
    $line = netstat -ano | Select-String -Pattern "^\s*TCP\s+127\.0\.0\.1:$Port\s+.*LISTENING\s+(\d+)\s*$" | Select-Object -First 1
    if (-not $line) { throw "No listener found on 127.0.0.1:$Port" }
    return [int]$line.Matches[0].Groups[1].Value
}

function Get-StackMemory($Pids) {
    $rows = foreach ($entry in $Pids.GetEnumerator()) {
        $process = Get-Process -Id $entry.Value -ErrorAction Stop
        [pscustomobject]@{ service = $entry.Key; pid = $process.Id; rss_mib = [math]::Round($process.WorkingSet64 / 1MB, 2) }
    }
    [pscustomobject]@{
        services = @($rows)
        total_rss_mib = [math]::Round(($rows | Measure-Object rss_mib -Sum).Sum, 2)
    }
}

function Invoke-Measurement([hashtable]$Body) {
    $watch = [Diagnostics.Stopwatch]::StartNew()
    try {
        $response = Invoke-RestMethod "$ApiBase/analyze" -Method Post -ContentType 'application/json' -Body ($Body | ConvertTo-Json -Compress) -TimeoutSec 180
        $watch.Stop()
        return [pscustomobject]@{ status = 200; elapsed_ms = [math]::Round($watch.Elapsed.TotalMilliseconds, 2); body = $response }
    } catch {
        $watch.Stop()
        $status = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
        return [pscustomobject]@{ status = $status; elapsed_ms = [math]::Round($watch.Elapsed.TotalMilliseconds, 2); body = $null }
    }
}

$ready = Invoke-RestMethod "$ApiBase/ready" -TimeoutSec 15
$dashboardStatus = (Invoke-WebRequest $DashboardUrl -UseBasicParsing -TimeoutSec 15).StatusCode
$pids = [ordered]@{
    api = Get-ListenerPid 8000
    dashboard = Get-ListenerPid 5173
    database = Get-ListenerPid 3306
}
$initialMemory = Get-StackMemory $pids

$short = @()
for ($index = 0; $index -lt $ShortRequests; $index++) {
    $short += Invoke-Measurement @{ text = "Research performance fixture $index. Basahin ang official source bago mag-share." }
}
if (($short | Where-Object status -ne 200).Count -gt 0) { throw 'A short performance request failed' }

$longText = (('Basahin ang buong artikulo at suriin ang source. ' * 350) + 'LIVE_STACK_COMPLETE_TAIL')
$long = Invoke-Measurement @{ text = $longText }
if ($long.status -ne 200 -or -not $long.body.analyzed_text.EndsWith('LIVE_STACK_COMPLETE_TAIL')) { throw 'Long-input measurement failed or truncated text' }

$client = [Net.Http.HttpClient]::new()
$concurrentBodies = 1..3 | ForEach-Object {
    $payload = @{ text = (('Suriin ang buong source at konteksto. ' * 220) + " concurrent-$_") } | ConvertTo-Json -Compress
    [Net.Http.StringContent]::new($payload, [Text.Encoding]::UTF8, 'application/json')
}
$concurrentWatch = [Diagnostics.Stopwatch]::StartNew()
$tasks = @($concurrentBodies | ForEach-Object { $client.PostAsync("$ApiBase/analyze", $_) })
$peakMemory = $initialMemory
while (($tasks | Where-Object { -not $_.IsCompleted }).Count -gt 0) {
    $sample = Get-StackMemory $pids
    if ($sample.total_rss_mib -gt $peakMemory.total_rss_mib) { $peakMemory = $sample }
    Start-Sleep -Milliseconds 20
}
[Threading.Tasks.Task]::WaitAll([Threading.Tasks.Task[]]$tasks)
$concurrentWatch.Stop()
$concurrentStatuses = @($tasks | ForEach-Object { [int]$_.Result.StatusCode })
$tasks | ForEach-Object { $_.Result.Dispose() }
$concurrentBodies | ForEach-Object { $_.Dispose() }
$client.Dispose()

$retrieval = Invoke-Measurement @{ text = 'PAGASA official weather advisory Philippines'; retrieve_sources = $true }
if ($retrieval.status -ne 200) { throw 'Live retrieval measurement failed' }

$latencies = @($short.elapsed_ms | Sort-Object)
$median = if ($latencies.Count % 2) { $latencies[[math]::Floor($latencies.Count / 2)] } else { ($latencies[$latencies.Count / 2 - 1] + $latencies[$latencies.Count / 2]) / 2 }
$p95Index = [math]::Min($latencies.Count - 1, [math]::Max(0, [math]::Ceiling($latencies.Count * 0.95) - 1))
$report = [ordered]@{
    passed = $true
    measured_at_utc = [DateTime]::UtcNow.ToString('o')
    scope = 'Native Windows live API, Vite dashboard and portable MariaDB; isolated synthetic requests. Not a Docker/Linux capacity result.'
    ready = [bool]$ready.ready
    dashboard_status = $dashboardStatus
    process_ids = $pids
    initial_memory = $initialMemory
    peak_sampled_stack_memory = $peakMemory
    short_requests = $ShortRequests
    short_http_ms = @($short.elapsed_ms)
    short_median_ms = [math]::Round($median, 2)
    short_p95_ms = [math]::Round($latencies[$p95Index], 2)
    long_http_ms = $long.elapsed_ms
    long_complete_tail = $true
    concurrent_statuses = $concurrentStatuses
    concurrent_elapsed_ms = [math]::Round($concurrentWatch.Elapsed.TotalMilliseconds, 2)
    retrieval_http_ms = $retrieval.elapsed_ms
    retrieval_status = $retrieval.body.retrieval_status
    retrieval_links = @($retrieval.body.related_sources).Count
    limitations = @('Single workstation run; no SLA or population-capacity claim.', 'Memory is listener-process RSS and excludes browser test processes.', 'Container build, Linux resource behavior and TLS remain unmeasured here.')
}
$json = $report | ConvertTo-Json -Depth 8
$json | Set-Content (Join-Path $root 'docs/LIVE-STACK-PERFORMANCE.json') -Encoding utf8
$json

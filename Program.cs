using System.Collections.Concurrent;
using System.Diagnostics;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddHttpClient("openai", client => client.Timeout = Timeout.InfiniteTimeSpan);
builder.Services.AddSingleton<JobStore>();
builder.Services.AddSingleton<OpenAiGateway>();
var app = builder.Build();

app.MapGet("/health", () => Results.Ok(new { status = "ok", service = "nba-cv-engine", version = "0.1.0" }));

app.MapPost("/v1/jobs", async (JobRequest request, JobStore jobs, CancellationToken ct) =>
{
    if (string.IsNullOrWhiteSpace(request.Input) || string.IsNullOrWhiteSpace(request.Output))
        return Results.BadRequest(new { error = "input and output are required" });
    var job = await jobs.StartAsync(request, ct);
    return Results.Accepted($"/v1/jobs/{job.Id}", job);
});
app.MapGet("/v1/jobs/{id}", (string id, JobStore jobs) =>
    jobs.TryGet(id, out var job) ? Results.Ok(job) : Results.NotFound());

// OpenAI-compatible endpoint. Set OPENAI_BASE_URL and OPENAI_API_KEY for upstream calls.
app.MapPost("/v1/chat/completions", async (HttpRequest http, OpenAiGateway gateway, CancellationToken ct) =>
    await gateway.ProxyChatAsync(http, ct));

app.MapPost("/v1/responses", async (HttpRequest http, OpenAiGateway gateway, CancellationToken ct) =>
    await gateway.ProxyRawAsync("responses", http, ct));

app.Run();

public sealed record JobRequest(
    string Input,
    string Output,
    string? Python = null,
    string? Arguments = null,
    string? SceneLabels = null,
    string[]? AllowedScenes = null);

public sealed record JobState(string Id, string Status, DateTimeOffset CreatedAt,
    DateTimeOffset? FinishedAt, string Input, string Output, string? Error,
    int ExitCode, string[]? AllowedScenes);

public sealed class JobStore
{
    private readonly ConcurrentDictionary<string, JobState> _jobs = new();
    public bool TryGet(string id, out JobState? state) => _jobs.TryGetValue(id, out state);

    public Task<JobState> StartAsync(JobRequest request, CancellationToken ct)
    {
        var id = $"job-{DateTimeOffset.UtcNow:yyyyMMddHHmmss}-{Guid.NewGuid():N}";
        var current = new JobState(id, "queued", DateTimeOffset.UtcNow, null, request.Input, request.Output, null, -1, request.AllowedScenes);
        _jobs[id] = current;
        _ = RunAsync(id, request, CancellationToken.None);
        return Task.FromResult(current);
    }

    private async Task RunAsync(string id, JobRequest request, CancellationToken ct)
    {
        _jobs[id] = _jobs[id] with { Status = "running" };
        try
        {
            var python = string.IsNullOrWhiteSpace(request.Python) ? "python" : request.Python;
            var args = request.Arguments ?? "";
            var psi = new ProcessStartInfo(python, args) { RedirectStandardOutput = true, RedirectStandardError = true, UseShellExecute = false, CreateNoWindow = true };
            psi.Environment["NBA_CV_JOB_ID"] = id;
            psi.Environment["NBA_CV_SCENE_LABELS"] = request.SceneLabels ?? "";
            using var process = Process.Start(psi) ?? throw new InvalidOperationException("could not start Python worker");
            var stdout = process.StandardOutput.ReadToEndAsync(ct);
            var stderr = process.StandardError.ReadToEndAsync(ct);
            await process.WaitForExitAsync(ct);
            var error = process.ExitCode == 0 ? null : (await stderr).Trim();
            _jobs[id] = _jobs[id] with { Status = process.ExitCode == 0 ? "succeeded" : "failed", FinishedAt = DateTimeOffset.UtcNow, Error = error, ExitCode = process.ExitCode };
        }
        catch (Exception ex) when (ex is not OperationCanceledException)
        {
            _jobs[id] = _jobs[id] with { Status = "failed", FinishedAt = DateTimeOffset.UtcNow, Error = ex.Message, ExitCode = -1 };
        }
    }
}

public sealed class OpenAiGateway
{
    private readonly IHttpClientFactory _factory;
    private readonly string _baseUrl = Environment.GetEnvironmentVariable("OPENAI_BASE_URL") ?? "https://api.openai.com/v1";
    private readonly string? _apiKey = Environment.GetEnvironmentVariable("OPENAI_API_KEY");
    public OpenAiGateway(IHttpClientFactory factory) => _factory = factory;

    public Task<IResult> ProxyChatAsync(HttpRequest request, CancellationToken ct) => ProxyRawAsync("chat/completions", request, ct);

    public async Task<IResult> ProxyRawAsync(string path, HttpRequest request, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(_apiKey)) return Results.Problem("OPENAI_API_KEY is not configured", statusCode: 503);
        using var reader = new StreamReader(request.Body);
        var body = await reader.ReadToEndAsync(ct);
        using var upstream = new HttpRequestMessage(HttpMethod.Post, $"{_baseUrl.TrimEnd('/')}/{path}") { Content = new StringContent(body, Encoding.UTF8, "application/json") };
        upstream.Headers.Authorization = new AuthenticationHeaderValue("Bearer", _apiKey);
        var response = await _factory.CreateClient("openai").SendAsync(upstream, HttpCompletionOption.ResponseHeadersRead, ct);
        request.HttpContext.Response.StatusCode = (int)response.StatusCode;
        request.HttpContext.Response.ContentType = response.Content.Headers.ContentType?.ToString() ?? "application/json";
        await response.Content.CopyToAsync(request.HttpContext.Response.Body, ct);
        return Results.Empty;
    }
}

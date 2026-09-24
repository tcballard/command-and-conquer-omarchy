// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.IO;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

namespace OpenRA.Mods.Omarchy
{
    // DTOs are deliberately independent of engine types for protocol tests.
    public sealed class AgentAction
    {
        public string kind { get; set; }
        public string actor { get; set; }
        public uint[] group { get; set; } = Array.Empty<uint>();
        public int[] cell { get; set; }
        public uint target { get; set; }
        public int count { get; set; } = 1;
    }

    public sealed class AgentReply
    {
        public int version { get; set; }
        public string token { get; set; }
        public int request { get; set; }
        public AgentAction action { get; set; }
        public string error { get; set; }
        public AgentMetrics metrics { get; set; }
    }

    public sealed class AgentMetrics
    {
        public int input_bytes { get; set; }
        public int elapsed_ms { get; set; }
    }

    public sealed class AgentEnvelope
    {
        public int request { get; set; }
        public int epoch { get; set; }
        public int deadline { get; set; }
        public AgentAction action { get; set; }
    }

    public static class AgentProtocol
    {
        public const int MaxReplyBytes = 8192;
        public static async Task<string> ReadLine(StreamReader reader)
        {
            var line = new StringBuilder();
            var one = new char[1];
            while (await reader.ReadAsync(one, 0, 1) != 0)
            {
                if (one[0] == '\n')
                    return line.ToString();
                if (line.Length >= MaxReplyBytes)
                    throw new InvalidDataException("Reply too large");
                line.Append(one[0]);
            }
            throw new EndOfStreamException("Runner disconnected");
        }

        public static AgentReply Parse(string json, string token, int request)
        {
            if (json.Length > MaxReplyBytes)
                throw new InvalidDataException("Reply too large");
            var reply = JsonSerializer.Deserialize<AgentReply>(json, new JsonSerializerOptions { MaxDepth = 8 });
            if (reply == null || reply.version != 1 || reply.token != token || reply.request != request)
                throw new InvalidDataException("Invalid session or request");
            if (reply.error != null)
            {
                if (reply.action != null || (reply.error != "configuration" && reply.error != "provider_unavailable" &&
                    reply.error != "provider_timeout" && reply.error != "invalid_model_action" &&
                    reply.error != "context_limit" && reply.error != "request_limit"))
                    throw new InvalidDataException("Invalid runner failure");
            }
            else Shape(reply.action);
            if (reply.metrics != null && (reply.metrics.input_bytes < 0 || reply.metrics.input_bytes > 24000 ||
                reply.metrics.elapsed_ms < 0 || reply.metrics.elapsed_ms > 60000))
                throw new InvalidDataException("Invalid decision metrics");
            return reply;
        }

        public static void Shape(AgentAction a)
        {
            if (a == null || a.group == null || a.group.Length > 32 || a.count < 1 || a.count > 5 ||
                (a.actor != null && (a.actor.Length > 64 || !System.Text.RegularExpressions.Regex.IsMatch(a.actor, "^[a-z0-9_.-]+$"))))
                throw new InvalidDataException("Invalid action shape");
            switch (a.kind)
            {
                case "wait": case "produce": case "deploy": case "attack": case "stop": break;
                case "place": case "move": case "defend": case "set_rally":
                    if (a.cell == null || a.cell.Length != 2 || Math.Abs((long)a.cell[0]) > 4096 || Math.Abs((long)a.cell[1]) > 4096)
                        throw new InvalidDataException("Invalid cell");
                    break;
                default: throw new InvalidDataException("Unknown action");
            }
        }
    }
}

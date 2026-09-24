// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.Text.RegularExpressions;

namespace OpenRA.Mods.Omarchy
{
    public static class AgentLaunch
    {
        public static string Provider => Environment.GetEnvironmentVariable("OMARCHY_AGENT_MODE");
        public static bool Model => Provider == "codex" || Provider == "ollama";
        public static bool Enabled => Model || Environment.GetEnvironmentVariable("OMARCHY_AGENT_TEST") == "1";
        public static string BotType => Model ? "omarchy-agent-model" : "omarchy-agent-test";
        public static string ModelName
        {
            get
            {
                var name = Environment.GetEnvironmentVariable("OMARCHY_AGENT_MODEL") ?? "";
                return Regex.IsMatch(name, "^[A-Za-z0-9][A-Za-z0-9_./:-]{0,95}$") ? name : "unconfigured";
            }
        }
    }
}

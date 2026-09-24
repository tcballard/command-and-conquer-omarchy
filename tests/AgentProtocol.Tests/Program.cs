using System;
using System.IO;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using OpenRA.Mods.Omarchy;

class Program
{
    static int cases;
    static void Reject(Action action)
    {
        try { action(); }
        catch (Exception e) when (e is InvalidDataException || e is JsonException) { cases++; return; }
        throw new Exception("Invalid input was accepted");
    }
    static async Task Main()
    {
        var good = "{\"version\":1,\"token\":\"session\",\"request\":7,\"action\":{\"kind\":\"produce\",\"actor\":\"powr\"}}";
        if (AgentProtocol.Parse(good, "session", 7).action.actor != "powr") throw new Exception();
        Reject(() => AgentProtocol.Parse(good, "another-session", 7));
        Reject(() => AgentProtocol.Parse(good, "session", 8));
        Reject(() => AgentProtocol.Parse(good.Replace("\"version\":1", "\"version\":2"), "session", 7));
        Reject(() => AgentProtocol.Parse("null", "session", 7));
        Reject(() => AgentProtocol.Parse("{", "session", 7));
        Reject(() => AgentProtocol.Parse(good.Replace("powr", "../../file"), "session", 7));
        Reject(() => AgentProtocol.Parse(good.Replace("produce", "execute_shell"), "session", 7));
        Reject(() => AgentProtocol.Shape(new AgentAction { kind = "move", cell = new[] { int.MinValue, 0 } }));
        Reject(() => AgentProtocol.Shape(new AgentAction { kind = "attack", group = new uint[33] }));
        Reject(() => AgentProtocol.Shape(new AgentAction { kind = "produce", count = -1 }));
        Reject(() => AgentProtocol.Shape(new AgentAction { kind = "stop", group = null }));
        using var large = new StreamReader(new MemoryStream(Encoding.UTF8.GetBytes(new string('a', 9000))));
        try { await AgentProtocol.ReadLine(large); throw new Exception("Oversize input accepted"); }
        catch (InvalidDataException) { cases++; }
        using var closed = new StreamReader(new MemoryStream());
        try { await AgentProtocol.ReadLine(closed); throw new Exception("EOF accepted"); }
        catch (EndOfStreamException) { cases++; }
        Console.WriteLine($"Valid round trip and {cases} rejection/disconnect cases passed.");
    }
}

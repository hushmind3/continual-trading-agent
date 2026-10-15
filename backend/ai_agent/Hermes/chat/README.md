# Chat

HTTP start/status/stop adapters call the imported `AIAgent.run_conversation`, output callbacks and interrupt API in the isolated worker. No custom agent loop. State polling does not launch a model or start a task.

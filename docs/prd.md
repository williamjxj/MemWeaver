Based on above and attached references, design a plan how to implement in macbook pro: use Ollama+LLM-Wiki+Agent-Skils together as second-brain for dynamic and consistent memory processing. 
Design the architecture, tech full-stack, 3rd tools/apis/cloud saas etc.

Please refere to the following which is a rough workflow I have in mind.
1. at the beginning, Chat APP ask a question to public LLM
2. public LLM return answer
3. Chat APP extracts Question and Answer after chat
4. It pass the Qestion+Answer pair to internal gateway/delegator/middle layer
5. the delegator ingest Q/A pair to Ollama LLM to generate a wiki-alike summary, like Karpathy's LLM-wiki 'ingest' process.
6. the wiki will be saved in wiki-alike system with indexed.
7. here LLM-wiki should be refer to Agent-Skill mechamism as well, to bring helpful and useful ideas
8. LLM-wiki raw: input Q+A pair
9. LLM-wiki wiki: indexed(Agent-skills) incremental graphify kb memory
10. Next time, when Chat APP ask a question, the Q will pass to delegator firstly, to query/retrieve Wiki/Agent-Skill-memory to get similar topic summary
11. Chat APP will use Q + the-summary-memory to send to public LLM via API
12. loop the above

In this way, the incremental llm-wiki knowledge feedbacks as user prompt, the App will become more and more smart and knowledgable without memory size limit.

### Extra-resource

- [llm-wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- [Agent Skills](https://agentskills.io/home): keyword trigger and Skills category
- memoryLLM, [M+](https://research.ibm.com/publications/m-extending-memoryllm-with-scalable-long-term-memory)
- LangChain, LLamaIndex
- Ollama






query="牙刷"
top_k=5

curl -X POST "http://127.0.0.1:18081/recommend" \
  -H "Content-Type: application/json" \
  -d '{"query":"${query}","top_k":${top_k}}'

curl -X POST "http://127.0.0.1:8081/recommend" \
  -H "Content-Type: application/json" \
  -d '{"query":"枕头","top_k":5}'

curl -s https://127.0.0.1:30003/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{{"messages": [{{"role": "user", "content": "What is the capital of France?"}}]}}'

  
curl -X POST "http://143.89.224.14:8081/recommend" \
  -H "Content-Type: application/json" \
  -d '{"query":"枕头","top_k":5}'

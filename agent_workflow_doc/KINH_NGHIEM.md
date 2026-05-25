File duy nhất trong dự án được viết thủ công :b 

## Để làm dự án 
* Cái ni cũ r nha, đọc cái "kinh nghiệm mới hơn" ở dưới. Cái này đọc phiên phiến tham khảo thôi
1. Đọc README của FANG và miCareer-mini, từ đó tỏa ra đọc các file strategy quan trọng. Cốt lõi để hiểu được cơ bản 2 code base này
2. Tùy vào việc cần làm trong phiên, thường me chọn sử dụng AI như Gemini FLask hay CLaude Haiku để hỗ trợ hiểu dự án + check tiến độ
3. Khi đã hiểu cơ bản và xác định được việc muốn làm. Trước hết vẫn phải dùng mô hình nhẹ (Flask, Haiku) để trình bày ra việc mình muốn làm -> hỏi để làm rõ hơn về ý định, yêu cầu và cân đo đong đếm cơ bản v.v Cần thiết thì gom cụm vấn đề và dùng Google Deep research để nghiên cứu sâu.
4. Sau khi đã thấy oke về task và có nền tảng nghiên cứu vững chắc, sử dụng Claude Sonnet để xây dựng chiến lược + bản kế hoạch thực thi chi tiết (sửa DB nào, sửa thế nào, sửa hàm nào, sửa thế nào, làm hàm mới nào, hàm mới đó làm gì, liên kết tất cả chúng với nhau v.v Cơ bản là nhìn vào là Code được ngay) 
5. Triển khai, thông thường me sẽ chia kế hoạch thành các pha, thường là 3-5 đối với một tính năng to ví dụ như NMAIex. Cơ bản kế hoạch có chiến lược rõ ràng, có kiến trúc và tài liệu triển khai nhìn là Code được thì:
    - Đối với các task đơn giản kiểu CRUD hoặc chỉ định rất rõ không cần tư duy gì thêm thì cho Gemini Flask làm (hoặc Haiku nhưng me chưa thử)
    - Khó hơn tý mà bắt đầu code đến nhiều hàm, nhiều file thì dùng GPT Codex hoặc Gemini Pro (low-high tùy biến)
    - Đối với các task mà các Model trước bất lực hoặc review code thấy chúng nó không đủ trình làm thì mới sử dụng Claude Sonnet để code (Căng nữa thì dùng hẳn Opus nhưng me chưa bao giờ dùng đến cả) (Thực ra nếu có dư thfi ae cứ bào Sonnet thật mạnh chứ gần như task phải khá dễ, tư duy ít thì mới tin Gemini hay Codex được. Sonnet code thì miễn chê, mỗi tội Anthropic bóp token nên hay bị over token limit)
6. Khi xong rồi thì thường me sẽ dùng một Model nhỏ đến tầm trung để cập nhật toàn bộ tài liệu dự án (Các tài liệu quan trọng như strategy hoặc guide thì vẫn nên dùng Sonnet để biết, cập nhật nhỏ không tư duy nhiều thì dùng đến Gemini Pro thôi)
7. Có 2 phương án, một là xong hẳn thì nghỉ ngơi thôi. Còn chưa xong mà hết token thì cũng nghỉ sớm :b (hoặc cần lắm thì bào credit bằng overages)

## Mấy thứ lặt vặt
- Thi thoảng làm việc 1-2 tuần thì me sẽ ngồi vui vui xem lại quá trình mình dev và nghĩ đến làm Skill. Những việc lặt vặt hoặc những prompt phải dạy đi dạy lại thì mình sẽ gom lại vào 1 skill để trong agent_workflow_doc. Ví dụ:
    - 'AI_MANUAL_UPDATE' để Agent tự lên mạng kiếm thông tin về các Model LLM dự án dùng và sau đó tự động cập nhật tại các tài liệu Code liên quan (cập nhật context size, thông báo deprecation v.v )
    - 'GIT_WORKFLOW_GUIDE' để Agent tự biết cách rẽ nhánh, commit theo chuẩn mình yêu cầu 
    - 'AI_WORKFLOW_INIT' để Agent khởi tạo ngữ cảnh, tự biết đi tìm tài liệu đọc hiểu dự án v.v

- Nên thêm đường dẫn tới "postgresql\bin\" trong system PATH để Agent tự gọi psql để query trực tiếp tới PostgreSQL local
- Cài chrome-devtools-mcp trong antigravity
- Cài postman MCP trong antigravity để Agent test API 

- Chỉ dẫn Agent dùng psql với tham số xem trong .env
- Yêu cầu Agent đọc file bằng "-Encoding UTF8" trong powershell tránh lỗi mojibake

## Quan trọng lắm này
- Làm việc với Agent, ít nhất là ở thời điểm hiện tại thì chưa thể tin tưởng được chúng nó đâu =))
    - Phải duyệt phương án triển khai, chiến lược rất kỹ. Đôi khi sửa đi sửa lại chục lần
    - Trong quá trình nó thực thi (tự đọc code, search web, triển khai v.v) phải ngồi đọc suy nghĩ nó liên tục. Để nó tự làm thì mất ổ C lúc nào không biết đâu :b. Đùa thôi nhưng mà thực sự giám sát liên tục lúc nó làm việc mới thấy vẫn còn phải chỉnh khá nhiều, nhất là khi nó bị hallucination mà mình không chặn kịp thì nó quậy cho hỏng hết.
    - Nhất là lúc chúng nó đưa ra phương án xong bảo là đợi mình duyệt mà toàn tự duyệt r làm luôn. Lúc đấy mà không quan sát thì nó tự triển khai lung tung thì ăn đủ :b Tốn token chỉ để sửa r làm lại từ đầu
   * Cập nhật - 23/05/2026 - Hưng: Hiện tại một số Model như GPT 5.5, Claude Opus 4.6 và Gemini Flask 3.5 đã khá oke, giờ mình bớt phải giám sát trực tiếp nữa rồi :b
- Khi dùng Agent làm việc dài, ưu tiên yêu cầu nó báo cáo plan, assumptions, drift/conflict mới phát hiện và output kiểm chứng được. Tier 2 không được tự đổi quyết định kiến trúc đã khóa trong tài liệu tier 1, có ý kiến thì viết report propsose rồi tier 1 review 1 thể.

## Những gì mình đang có
* Cập nhật - 23/05/2026 - Hưng
- Codex dùng gói ChatGPT Plus: GPT 5.5 siêu ngoăn, giờ đang có gói Plus miễn phí 1 tháng khuyên ae đớp ngay kẻo hết nhé
- Antigravity/Antigravity IDE dùng gói Google AI Pro: có Gemini 3.5 Flash, Gemini 3.1 Pro, Claude Sonnet 4.6 và Claude Opus 4.6.
- GitHub Copilot gói Pro Student: khuyến khích ae đớp ngay nhé dùng Haiku trong đó okela lắm.

## Phân tầng model để dùng
1. **Tier 1 - quyết định khó và tài liệu chỉ huy:** GPT-5.5 hoặc Claude Opus 4.6.
   - Dùng khi cần đọc rộng toàn repo, đối chiếu code với docs, phân tích kiến trúc, quyết định hướng refactor, viết tài liệu định hướng để model khác làm theo.
   - Với task thật khó hoặc cần phản biện kỹ thì tăng reasoning lên high/xhigh hoặc cho GPT-5.5 và Opus review chéo.
2. **Tier 2 - thực thi theo spec rõ:** GPT-5.4, Claude Sonnet 4.6, Gemini 3.5 Flash.
   - Dùng để code, sửa docs, làm test/eval seed, làm report theo tài liệu tier 1 đã quyết định rõ scope, file cần đụng, tiêu chí xong.
   - Task càng rõ và hẹp thì dùng reasoning low/medium trước. Tăng lên high khi có nhiều file, nhiều ràng buộc hoặc debug dai.
3. **Tier nhẹ - hỏi nhanh và việc nhỏ:** Claude Haiku/Gemini Flash hoặc model nhẹ khác đang sẵn trong IDE.
   - Dùng để giải thích đoạn code, gợi ý edit nhỏ, tìm điểm tham chiếu, check lại checklist.

## Kinh nghiệm mới hơn
1. Đọc README của FANG và miCareer-mini, từ đó tỏa ra đọc các file strategy/guide/workflow quan trọng theo đúng phạm vi việc đang làm. Khi task lớn hoặc repo đã drift nhiều thì ưu tiên để tier 1 dựng lại tình trạng dự án thực tế trước để hiểu rõ hơn trước khi làm.
2. Dự án đã ổn định hơn giai đoạn đầu. Với phần lớn câu hỏi mới, có thể để Agent đọc repo, search web có chọn lọc và tự suy luận để tư vấn trước. Google/GPT Deep Research vẫn giữ cho vấn đề cần nền tảng nghiên cứu sâu, nhiều nguồn, có tranh luận hoặc ảnh hưởng lớn đến kiến trúc/chất lượng.
3. Khi ý định còn mơ hồ, dùng model nhẹ hoặc tier 2 để làm rõ bài toán, gom câu hỏi, bóc ràng buộc. Khi bài toán đã rõ nhưng quyết định khó, chuyển lên tier 1 để viết strategy/decision memo/implementation plan.
4. Với đầu việc quan trọng, tier 1 nên viết tài liệu đủ chi tiết để tier 2 thực thi như đọc đề bài:
   - Vấn đề và lý do phải làm.
   - Quyết định đã chốt và điều chưa được tự ý quyết.
   - File cần đọc, file dự kiến tạo/sửa, ownership và thứ tự thực hiện.
   - Output, acceptance criteria, test/report cần trả về.
5. Triển khai theo cụm ít phụ thuộc nhau. Cùng một người/agent nên ôm trọn cụm có vòng đời thống nhất, ví dụ việc xem xét lại prompt engineering (review full chỗ dùng LLM trong dự án) + eval tối thiểu, hoặc nâng cấp JobApplication chat + docs/tests/UI liên quan.
6. Với code:
   - Task đơn giản, spec rất rõ, CRUD/docs/checklist thì giao tier 2 hoặc tier nhẹ phù hợp.
   - Task nhiều file nhưng kiến trúc đã quyết thì dùng GPT-5.4/Sonnet/Gemini 3.5 Flash theo công cụ tiện nhất.
   - Task đụng core, migration lớn, agent/tool architecture, hoặc review thấy tier 2 làm không ổn thì đưa lại tier 1.
7. Với docs:
   - Trước tiên phải biết truth source và loại drift: docs sửa theo code, code sửa theo docs, hay tài liệu cũ cần archive/viết lại.
   - Cập nhật nhỏ giao tier 2 được. Strategy, guide quan trọng hoặc doc reconciliation lớn cần có plan/review của tier 1.

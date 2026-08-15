# Copilot SDK 기반 Claude 대안 검토

최종 업데이트: 2026-08-15

## 핵심 결론

이 방식은 다음 상황에 적합한 **임시 기술 경로**다.

> 한국 Foundry Marketplace에서 Claude를 직접 배포하기 어려울 때,
> Copilot 라이선스를 가진 고객사의 내부 Agent와 워크플로에서 Claude 사용
> 가능성을 검증한다.

**권장:**

- 고객사 내부 PoC와 데모
- Copilot Business/Enterprise를 보유한 임직원용 업무 Agent
- 중간 규모의 텍스트 생성·검토·분류·요약 워크플로

**추가 검토 없이 권장하지 않음:**

- 불특정 외부 고객을 위한 공개 SaaS
- 한국 데이터 레지던시가 필수인 서비스
- 고정 TPS와 모델 endpoint SLA가 필요한 서비스
- 하나의 개인 PAT를 여러 고객이 공유하는 production 구조

이 방식은 Azure Marketplace를 통한 Claude 구매 또는 Foundry Claude model
deployment와 동일하지 않다. 모델 인증·사용량·정책·과금은 GitHub Copilot에
귀속된다.

## 30초 의사결정

| 요구사항 | 판단 |
|---|---|
| Claude가 필요한 내부 PoC | 적합 |
| 모든 사용자가 Copilot 좌석 보유 | 적합 |
| 사용자별 GitHub OAuth 적용 가능 | production 후보 |
| 하나의 PAT로 소규모 제한 사용 | PoC만 권장 |
| 한국 region 내 추론 필수 | 부적합 |
| 공개 model API처럼 대량 호출 | 별도 capacity 검증 필요 |
| Foundry RBAC·endpoint·버전 관리 필요 | Hosted Agent 조합이 유효 |

## 1. 검토 배경

한국 Azure의 Microsoft Foundry Marketplace 제약으로 Claude 모델을 직접
배포하기 어려운 기간에, GitHub Copilot SDK가 제공하는 Claude 모델을
Foundry Hosted Agent 안에서 호출하는 방식을 임시 대안으로 검토할 수 있다.

이 리포는 다음 경로를 실제로 구현하고 실행한 기술 PoC다.

```text
Client
  -> Microsoft Foundry Hosted Agent
  -> GitHub Copilot SDK runtime
  -> Claude Opus 5 provided through GitHub Copilot
```

Claude Opus 5는 고객의 Foundry account에 model deployment로 생성되지
않는다. Foundry는 Agent 코드와 endpoint를 호스팅하고, 모델 인증·사용량·정책은
GitHub Copilot 계정에 귀속된다.

### 책임 경계

| 계층 | 담당 |
|---|---|
| Agent 코드와 workflow | 이 애플리케이션 |
| Agent endpoint, 버전, 실행 환경 | Microsoft Foundry |
| Agent 내부 session과 모델 호출 | GitHub Copilot SDK |
| Claude 모델 제공, 정책, quota, 과금 | GitHub Copilot |
| 실제 Claude hosting | AWS, Anthropic PBC 또는 Google Cloud |

## 2. 이 PoC가 증명하는 것

- Foundry에 Claude model deployment가 없어도 Hosted Agent를 실행할 수 있다.
- Copilot SDK에서 `claude-opus-5` 모델을 명시적으로 선택할 수 있다.
- 개발·CI/CD가 아닌 일반 업무 Agent를 만들 수 있다.
- Writer -> Legal reviewer -> Formatter 형태의 sequential workflow가 동작한다.
- Foundry의 `invocations` endpoint를 통해 원격 서비스로 제공할 수 있다.
- Copilot SDK의 개발용 기본 도구를 제거하고 모델/session runtime만 사용할 수 있다.

## 3. 이 PoC가 증명하지 않는 것

- 다중 고객 환경의 production 인증과 사용자 격리
- 공개 SaaS에서 하나의 Copilot token을 공유해도 된다는 상업적 사용 권리
- 고정 TPS, 처리량 SLA 또는 무제한 호출
- 한국 region 내 모델 추론과 데이터 레지던시
- Foundry model deployment와 동일한 quota, chargeback 및 lifecycle 제어
- 장애 복구, workflow checkpoint, 단계별 재시도와 idempotency

따라서 이 구현은 **기술적 가능성을 보여주는 reference implementation**이며,
그 자체를 다중 고객 production 서비스로 간주하면 안 된다.

## 4. 적합한 적용 범위

| 시나리오 | 적합성 | 권장 인증 |
|---|---:|---|
| 고객사 내부 PoC와 데모 | 높음 | 제한된 전용 Copilot 계정 |
| Copilot Business/Enterprise를 보유한 임직원용 내부 Agent | 높음 | 사용자별 GitHub OAuth |
| 중간 규모의 일반 업무 workflow | 중간~높음 | 사용자별 token 또는 고객 소유 계정 |
| 하나의 token을 공유하는 부서 내부 서비스 | 중간 | 엄격한 rate limit과 비용 한도 |
| 불특정 외부 고객 대상 SaaS | 낮음 | GitHub의 서면 확인 없이 진행하지 않음 |
| 한국 데이터 레지던시가 필수인 workload | 낮음 | 다른 한국 region 지원 모델 검토 |

## 5. 권장 인증 모델

### 5.1 PoC: 전용 사용자 token

현재 리포가 사용하는 구조다. 하나의 GitHub token을 Hosted Agent 환경 변수로
주입한다.

장점:

- 구현이 단순하다.
- Claude 모델 접근 가능성을 빠르게 검증할 수 있다.

한계:

- 모든 사용량이 한 사용자에게 귀속된다.
- token이 rate limit과 장애의 단일 병목이 된다.
- 사용자별 감사, quota, 비용 배분이 어렵다.
- 장기 PAT rotation과 폐기 절차가 필요하다.

### 5.2 내부 서비스: 사용자별 GitHub OAuth

각 사용자가 GitHub OAuth App을 통해 로그인하고 자신의 GitHub user token을
사용하도록 한다. 사용자는 유효한 Copilot entitlement와 조직에서 허용한
Claude 모델 정책을 가져야 한다.

장점:

- 사용량과 권한을 사용자별로 귀속할 수 있다.
- 공유 PAT를 제거할 수 있다.
- 조직의 Copilot 정책과 budget을 그대로 적용할 수 있다.

추가 구현:

- OAuth callback과 token lifecycle
- 사용자별 Copilot client/session 격리
- tenant와 사용자별 storage 분리
- 로그에서 token과 민감정보 제거

### 5.3 고객 소유 Copilot 조직

고객이 Copilot Business/Enterprise 조직, 모델 정책, budget 및 OAuth App을
소유한다. 구현 제공자는 Hosted Agent 코드만 제공한다.

고객 환경별 비용과 정책 경계가 분리되므로 엔터프라이즈 납품에 가장 적합하다.

### 5.4 BYOK

Copilot SDK는 Anthropic 등 provider의 API key를 사용하는 BYOK도 지원한다.
이 경우 GitHub Copilot 구독 없이 runtime 기능을 사용할 수 있다.

단순 LLM 호출만 필요하다면 BYOK Copilot SDK보다 Anthropic SDK를 직접 쓰는
편이 가볍다. Copilot SDK의 planning, session, tools, skills가 필요한 경우에만
BYOK가 의미가 있다.

## 6. Quota와 비용

Copilot SDK 표준 사용은 Copilot CLI와 같은 GitHub AI Credits 체계를 사용한다.
고정 호출 횟수가 아니라 input, cached input, cache write, output token을
모델별 가격으로 계산한다.

2026-08-15 기준 Claude Opus 5 가격:

| 항목 | 100만 token당 가격 |
|---|---:|
| Input | $5.00 |
| Cached input | $0.50 |
| Cache write | $6.25 |
| Output | $25.00 |

`1 AI credit = $0.01`다.

예를 들어 input 2,000 token과 output 1,000 token인 호출은 cache 비용을
제외하면 약 `$0.035`, 즉 3.5 credits다.

현재 workflow는 Writer, Legal reviewer, Formatter가 각각 모델을 호출하므로
한 번의 workflow 실행이 대략 5~15 credits를 사용할 수 있다. 실제 비용은
각 단계의 입력·출력 길이와 cache 사용량에 따라 달라진다.

2026-08-15 기준 조직 플랜의 포함량:

| 플랜 | 2026-09-01 전 프로모션 | 표준 월 제공량 |
|---|---:|---:|
| Copilot Business | 3,000 credits/seat | 1,900 credits/seat |
| Copilot Enterprise | 7,000 credits/seat | 3,900 credits/seat |

조직 또는 enterprise의 좌석별 credits는 billing entity 단위 pool로 합쳐진다.
추가 사용 정책과 budget을 허용하면 포함량을 초과해 계속 과금할 수 있다.

주의:

- GitHub의 rate limit은 AI Credits와 별개다.
- GitHub는 모델별 고정 TPS나 고객용 endpoint SLA를 공개적으로 보장하지 않는다.
- 하나의 token에 모든 traffic을 집중하면 조직 pool이 남아도 병목이 될 수 있다.
- 대량 traffic 전에는 실제 concurrency와 throttling을 부하 테스트해야 한다.

### 간단한 용량 산정

```text
월 예상 workflow 실행 수
  = 사용 가능한 월 AI Credits / workflow 1회 평균 Credits
```

예를 들어 3,000 credits와 평균 10 credits/run을 가정하면 약 300회다.
이는 비용 기준 추정치일 뿐이며, GitHub rate limit과 일시적 모델 capacity는
별도로 검증해야 한다.

Production 판단 전에는 실제 traffic과 유사한 payload로 다음 값을 측정한다.

- 단계별 input/output token
- workflow 1회 평균과 P95 Credits
- 동시 실행 수별 성공률과 latency
- throttle 발생 빈도와 retry 후 성공률

## 7. Region과 데이터 처리

이 리포의 실제 요청 경로는 다음과 같다.

```text
사용자
  -> Foundry Hosted Agent: North Central US
  -> GitHub Copilot
  -> Claude hosting: AWS, Anthropic PBC 또는 Google Cloud
```

GitHub 공식 문서는 Claude 모델이 AWS, Anthropic PBC, Google Cloud에서
호스팅된다고 설명하지만, 각 요청의 실제 처리 region을 한국으로 보장하지 않는다.

따라서:

- 한국 Azure region 내 처리로 간주할 수 없다.
- 한국 데이터 레지던시 요구사항을 충족한다고 주장하면 안 된다.
- 고객 보안, 법무, 개인정보 및 DPA 검토가 필요하다.
- 민감정보와 규제 데이터는 승인 전까지 전송하지 않는 것이 안전하다.

GA Claude 모델에 대해서는 GitHub와 provider의 비학습 및
zero-data-retention 약정이 적용된다. 단, preview 기능은 별도 조건이 있을 수
있으므로 활성 기능별 최신 문서를 확인해야 한다.

## 8. 일반 Agent Workflow 구현 시 고려사항

### 8.1 Workflow orchestration

Copilot SDK에는 Microsoft Agent Framework의 `WorkflowBuilder`와 같은 전용
workflow graph가 없다. 순차, 병렬, 분기, handoff를 애플리케이션 코드로
구현해야 한다.

Production 구현에 추가할 항목:

- 단계별 timeout과 retry
- idempotency key
- 실패 단계부터 재개할 checkpoint
- 단계별 입력·출력 schema validation
- 부분 실패와 보상 처리
- cancellation 전파

### 8.2 Tool safety

Copilot SDK는 기본적으로 파일, shell 등 강력한 개발 도구를 제공할 수 있다.
일반 업무 Agent에서는 다음 원칙을 적용한다.

- `mode="empty"` 사용
- `available_tools=[]` 또는 명시적인 allowlist
- 쓰기·삭제·결제 같은 action은 human approval
- tenant별 credential과 tool connection 분리
- tool argument와 result 감사 로그

### 8.3 Session과 tenant 격리

- 사용자와 tenant별 Copilot session ID 분리
- Foundry session과 Copilot session의 mapping 저장
- session filesystem 및 memory의 tenant 간 공유 금지
- 사용자 퇴사·권한 회수 시 session과 token 폐기

### 8.4 Observability

Foundry는 Hosted Agent endpoint와 container의 상태를 관측할 수 있지만,
Copilot SDK 내부의 각 workflow 단계가 자동으로 Foundry evaluation과 완전히
연결되는 것은 아니다.

다음을 별도 수집하는 것이 좋다.

- stage 이름과 처리 시간
- model ID
- input/output token과 AI Credits
- retry와 throttle 발생 횟수
- 사용자, tenant, correlation ID
- 단계별 품질 평가 점수

prompt와 응답 전문은 개인정보 및 영업비밀 정책에 따라 저장 여부를 결정한다.

### 8.5 Model policy와 fallback

- 조직 관리자가 Claude Opus 5를 허용했는지 시작 시 확인
- `list_models()`로 실제 모델 가용성을 검사
- 모델이 제거되거나 제한될 때 명시적으로 실패
- 자동 fallback을 쓴다면 품질·비용 차이를 사용자에게 고지
- fallback 후보와 평가 기준을 사전에 승인

## 9. Production readiness checklist

### 인증·라이선스

- [ ] 고객 시나리오에 GitHub Copilot SDK 사용이 허용되는지 확인
- [ ] 공유 PAT 대신 사용자별 OAuth 또는 고객 소유 계정 적용
- [ ] token 저장, rotation, 폐기 절차 수립
- [ ] 고객별 Copilot entitlement 확인

### 비용·용량

- [ ] Business/Enterprise AI Credits pool 확인
- [ ] 추가 사용 정책과 budget 설정
- [ ] 사용자·tenant별 비용 한도 적용
- [ ] 실제 payload 기반 token 비용 측정
- [ ] concurrency 및 rate-limit 부하 테스트

### 보안·규정

- [ ] 데이터 흐름과 subprocessor 검토
- [ ] 한국 데이터 레지던시가 아님을 명시
- [ ] 민감정보 분류와 전송 정책 정의
- [ ] prompt, output 및 tool log의 보존 정책 정의

### Workflow 안정성

- [ ] timeout, retry, idempotency 적용
- [ ] checkpoint와 실패 재개 구현
- [ ] schema validation 적용
- [ ] 단계별 telemetry와 alert 구성
- [ ] 모델 정책 변경 및 장애 fallback 시험

## 10. 권장 결론

PoC와 고객사 내부의 중간 규모 workflow에는 현실적인 선택이 될 수 있다.
불특정 외부 고객용 SaaS, 한국 데이터 레지던시가 필수인 서비스, 고정 TPS/SLA가
필요하다면 다른 모델 공급 경로 또는 GitHub와의 별도 상업·지원 협의를 먼저
진행해야 한다.

권장 진행 순서:

1. 이 리포로 기술 PoC와 모델 품질을 검증한다.
2. 고객의 Copilot 플랜, Claude 모델 정책, AI Credits pool을 확인한다.
3. 사용자별 OAuth 또는 고객 소유 Copilot 조직으로 인증을 분리한다.
4. 실제 payload로 비용, latency, concurrency와 rate limit을 측정한다.
5. 보안·법무 검토 후 제한된 내부 사용자부터 점진적으로 출시한다.

## 11. 공식 참고 자료

- [GitHub Copilot SDK](https://github.com/github/copilot-sdk)
- [GitHub OAuth setup](https://docs.github.com/copilot/how-tos/copilot-sdk/setup/github-oauth)
- [Models and pricing for GitHub Copilot](https://docs.github.com/copilot/reference/copilot-billing/models-and-pricing)
- [Usage-based billing for organizations and enterprises](https://docs.github.com/copilot/concepts/billing/usage-based-billing-for-organizations-and-enterprises)
- [Usage limits for GitHub Copilot](https://docs.github.com/copilot/concepts/usage-limits)
- [Hosting of models for GitHub Copilot](https://docs.github.com/copilot/reference/ai-models/model-hosting)
- [Foundry Hosted Agents](https://learn.microsoft.com/azure/ai-foundry/agents/concepts/hosted-agents)

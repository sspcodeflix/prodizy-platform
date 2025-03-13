## Background

The Decision System is the central intelligence component of the Prodizy Platform, responsible for analyzing user queries and determining the optimal path for fulfilling them. It orchestrates the interactions between various components and determines whether to leverage direct LLM knowledge, retrieve contextual information, or execute actions against enterprise systems.

## Architectural standpoint

Within the Prodizy Platform architecture, the Decision System occupies a pivotal position:

- **Upstream Connections**:

  - Receives processed queries from the LLM Connector Bridge
  - Receives API capability information from the Connector Registry
  - Receives feedback from the Execution Results Store

- **Downstream Connections**:
  - Directs the LLM Service for response generation
  - Instructs the RAG Engine for information retrieval
  - Sends execution requests to enterprise systems via the Connector Registry

## Internal Architecture

The Decision System itself has a layered internal architecture:

### 1. Query Analysis Layer

- **Intent Classification Module**:

  - Identifies the primary intent of the user query (information retrieval, action execution, analysis)
  - Uses a combination of rule-based patterns and ML classification
  - Maps intents to capability categories

- **Entity Extraction Module**:

  - Identifies key entities mentioned in the query
  - Extracts parameters, constraints, and contextual elements
  - Maps entities to system objects (e.g., "Jira ticket" → Jira issue object)

- **Context Management Module**:
  - Incorporates conversation history from the Session Store
  - Tracks entities and topics across turns
  - Resolves references and maintains subject continuity

### 2. Strategy Selection Layer

- **Capability Matching Module**:

  - Maps user intent to available system capabilities
  - Queries the Connector Registry to identify relevant APIs
  - Evaluates confidence in different execution paths

- **Execution Planning Module**:

  - Determines the optimal approach for fulfilling the request
  - Plans multi-step operations when needed
  - Identifies prerequisites for successful execution

- **Resource Selection Module**:
  - Chooses specific data sources or APIs based on relevance
  - Applies governance rules and access controls
  - Optimizes for performance and reliability

### 3. Execution Control Layer

- **Orchestration Module**:

  - Manages the sequence of operations across components
  - Handles synchronous and asynchronous execution flows
  - Coordinates parallel operations when appropriate

- **Error Handling Module**:

  - Detects and manages execution failures
  - Implements fallback strategies
  - Formulates appropriate error messages for users

- **Result Synthesis Module**:
  - Integrates results from multiple sources
  - Formats information for presentation to users
  - Determines when additional context is needed

## Decision Flow Process

When a user query enters the system, the Decision System follows this general workflow:

1. **Initial Processing**:

   - Receives the processed query from the LLM Connector Bridge
   - Activates the Query Analysis Layer for intent and entity extraction
   - Establishes the conversation context from the Session Store

2. **Path Determination**:

   - The Strategy Selection Layer evaluates the query against available capabilities
   - It generates a confidence score for different processing paths:
     - **Direct LLM Path**: For general knowledge or simple reasoning questions
     - **RAG Path**: For queries requiring enterprise-specific knowledge
     - **API Execution Path**: For actionable requests requiring system integration
     - **Hybrid Path**: Combining multiple approaches for complex requests

3. **Execution Flow**:

   - For **Direct LLM Path**:

     - Forwards the query directly to the LLM Service
     - Provides conversation context and response guidelines
     - Receives and validates the response

   - For **RAG Path**:

     - Instructs the RAG Engine to retrieve relevant context
     - Formulates an enhanced prompt including the retrieved information
     - Sends the enhanced prompt to the LLM Service

   - For **API Execution Path**:

     - Constructs API call parameters based on the query
     - Sends execution instructions to the Connector Registry
     - Processes the results and formats them for presentation

   - For **Hybrid Path**:
     - Orchestrates a sequence of operations across components
     - Manages dependencies between steps
     - Synthesizes a unified response from multiple outputs

4. **Feedback Loop**:
   - Records the decision path in the Execution Results Store
   - Captures performance metrics and outcome success
   - Updates confidence models based on results

## Integration with Other Components

### Integration with Connector Registry

The Decision System interacts with the Connector Registry to:

- Query available API capabilities matching user intent
- Retrieve parameter requirements for API execution
- Send structured API execution requests with appropriate parameters
- Receive execution results and status information

### Integration with RAG Engine

The Decision System directs the RAG Engine by:

- Formulating retrieval queries based on user intent
- Specifying the type of information needed for context enhancement
- Receiving retrieved information and incorporating it into LLM prompts
- Using retrieval results to inform API parameter selection

### Integration with LLM Service

The Decision System controls the LLM Service by:

- Constructing prompts that include appropriate context and instructions
- Specifying response parameters (format, length, style)
- Evaluating responses for quality and completeness
- Requesting clarification or elaboration when needed

### Integration with Execution Results Store

The Decision System both writes to and reads from the Execution Results Store:

- Records decisions made and their outcomes
- Retrieves historical execution patterns for similar queries
- Uses performance data to refine future decision strategies
- Implements learning from past successes and failures

## Technical Implementation

### Key Technologies

The Decision System utilizes several key technologies:

- **NLP Components**: For intent classification and entity extraction
- **Rules Engine**: For governance and compliance enforcement
- **ML Models**: For confidence scoring and path selection
- **Orchestration Framework**: For managing complex execution flows
- **Feedback Learning System**: For improving decisions over time

### State Management

The Decision System maintains several types of state:

- **Session State**: Current conversation context and history
- **Execution State**: Status of ongoing operations
- **Entity State**: Tracked entities and their attributes
- **Authorization State**: User permissions and access levels

### Performance Considerations

To ensure optimal performance, the Decision System implements:

- **Parallel Processing**: Where dependencies permit
- **Caching**: For frequently used capability information
- **Prioritization**: Of time-sensitive operations
- **Graceful Degradation**: When optimal paths are unavailable

## MVP-1 vs. MVP-2 Implementation

### MVP-1 Implementation

In the initial MVP, the Decision System focuses on:

- Basic intent classification using rule-based patterns
- Simple path selection for straightforward queries
- Limited orchestration capabilities for sequential operations
- Manual configuration of capability mappings
- Baseline error handling and fallback strategies

### MVP-2 Enhancements

Based on MVP-1 feedback, MVP-2 will expand the Decision System to include:

- ML-enhanced intent classification with confidence scoring
- Sophisticated execution planning for multi-step operations
- Learning from execution results to improve decision quality
- Dynamic capability discovery and mapping
- Advanced error recovery and alternative path suggestion
- User preference incorporation into decision strategies

## Business Impact

The Decision System's capabilities directly impact key business outcomes:

- **Accuracy**: Selecting the optimal path improves response quality
- **Efficiency**: Reducing unnecessary operations improves performance
- **Adaptability**: Learning from feedback enables system evolution
- **Governance**: Enforcing business rules ensures compliance
- **User Satisfaction**: Delivering the right information or action enhances experience

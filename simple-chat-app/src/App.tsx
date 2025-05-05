import { css, keyframes } from "@emotion/react";
import { ChangeEvent, useRef, useState } from "react";
import { MdError, MdSend } from "react-icons/md";
import { Button, Div, H1, H2, I, P, Span, Textarea } from "style-props-html";

const COMPLETION_SERVER_URL = "http://localhost:5000/completion"


const spin = keyframes`
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
`;

type DialogMessage = {
  role: "system" | "user" | "assistant";
  content: string;
};

const roleBgColors = {
  user: "blue",
  system: "purple",
  assistant: "green",
} as const;

const roleTextColors = {
  user: "white",
  system: "white",
  assistant: "white",
} as const;

function capitalize(text: string) {
  if (text.length === 0) {
    return text;
  }
  if (text.length === 1) {
    return text.toUpperCase();
  }
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function App() {
  const chatContainerRef = useRef<HTMLDivElement | null>(null);

  const [dialog, setDialog] = useState<DialogMessage[]>([]);

  // useEffect(() => {
  //   if (chatContainerRef.current) {
  //     chatContainerRef.current.scrollTo({
  //       top: chatContainerRef.current.scrollHeight,
  //       behavior: "smooth", // optional, for animated scroll
  //     });
  //   }
  // }, [dialog]); // will scroll every time messages update
  const [processingState, setProcessingState] = useState<
    "idle" | "loading" | "error"
  >("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [prompt, setPrompt] = useState<string>("");
  const promptLineCount = Math.max(prompt.split("\n").length, 1);
  async function sendMessage() {
    const newDialog = dialog.concat([
      {
        role: "user",
        content: prompt,
      },
    ]);
    setDialog(newDialog);
    setProcessingState("loading");
    try {
      const response = await fetch(COMPLETION_SERVER_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          messages: newDialog,
        }),
      });
      const textResponse = await response.text();
      if (response.ok) {
        const result = JSON.parse(textResponse) as DialogMessage;
        setDialog([
          ...newDialog,
          {
            role: result.role,
            content: result.content,
          },
        ]);
        setProcessingState("idle");
        setPrompt("");
      } else {
        if (response.status === 503) {
          setErrorMessage(
            "Ai server is busy. Refresh the page and try again soon."
          );
          setProcessingState("error");
        } else {
          throw {
            status: response.status,
            statusText: response.statusText,
            textResponse,
          };
        }
      }
    } catch (e) {
      console.error(e);
      if (e instanceof Error) {
        setErrorMessage(e.message);
      } else {
        setErrorMessage("Unknown Error");
      }
      setProcessingState("error");
    }
  }
  return (
    <Div
      width="100vw"
      height="100vh"
      overflow="auto"
      display="flex"
      flexDirection="column"
      alignItems="center"
      justifyContent="flex-start"
      gap="0.5rem"
      padding="0.5rem"
      ref={chatContainerRef}
    >
      <H1>Local LLM Chat</H1>
      <I>Llama 3.2 3B Instruct</I>
      {dialog.map((m, i) => (
        <Div
          key={i}
          width="100%"
          maxWidth="50rem"
          display="flex"
          flexDirection="column"
        >
          <H2
            width="100%"
            background={roleBgColors[m.role]}
            color={roleTextColors[m.role]}
            fontWeight="bold"
            padding="0.25rem"
            fontSize="1.25rem"
          >
            {capitalize(m.role)}
          </H2>
          <P
            width="100%"
            padding="0.25rem"
            fontSize="1rem"
            border={`1px solid ${roleBgColors[m.role]}`}
            whiteSpace="pre-wrap"
          >
            {m.content}
          </P>
        </Div>
      ))}

      {processingState === "idle" && (
        <>
          <Div
            width="100%"
            display="flex"
            alignItems="center"
            flexDirection="column"
          >
            <Textarea
              display="block"
              disabled={processingState !== "idle"}
              width="100%"
              maxWidth="50rem"
              padding="0.25em"
              fontSize="1rem"
              lineHeight="1.5"
              border="1px solid black"
              background="lightgrey"
              placeholder="Enter a prompt..."
              value={prompt}
              onChange={(e: ChangeEvent<HTMLTextAreaElement>) => {
                setPrompt(e.target.value);
              }}
              rows={promptLineCount}
              // minHeight={`calc( (${promptLineCount} * 1rem * 1.5 ) + (2 * 0.25rem) )`}
              resize="none"
            ></Textarea>
          </Div>

          <Button
            disabled={processingState !== "idle"}
            background="green"
            color="white"
            border="none"
            borderRadius="0.25rem"
            padding="0.25rem"
            fontSize="1.25rem"
            display="flex"
            flexDirection="row"
            alignItems="center"
            gap="0.2rem"
            onClick={sendMessage}
          >
            <MdSend />
            <Span>Send</Span>
          </Button>
        </>
      )}

      {processingState === "loading" && (
        <Div
          width="100%"
          height="2rem"
          display="flex"
          alignItems="center"
          justifyContent="center"
        >
          <Div
            width="2rem"
            height="2rem"
            border="3px solid blue"
            borderTop="3px solid transparent"
            borderRadius="50%"
            transformOrigin="center"
            css={css`
              animation: ${spin} 1s linear infinite;
            `}
          ></Div>
        </Div>
      )}
      {processingState === "error" && (
        <Div
          display="flex"
          flexDirection="row"
          alignItems="center"
          justifyContent="flex-start"
          gap="0.5rem"
          background="red"
        >
          <MdError />
          <P>{errorMessage ?? "Unknown Error"}</P>
        </Div>
      )}
    </Div>
  );
}

export default App;

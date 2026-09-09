import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ChatMarkdownProps {
  content: string;
}

export default function ChatMarkdown({ content }: ChatMarkdownProps) {
  return (
    <div className="chat-md">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ node, ...props }) => (
            <a {...props} target="_blank" rel="noopener noreferrer" />
          ),
          table(props) {
            return (
              <div className="chat-table-wrap">
                <table {...props} />
              </div>
            );
          },
          li({ node, ...props }) {
            return <li {...props} className="chat-li" />;
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

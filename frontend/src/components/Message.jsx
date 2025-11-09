import { Bot, CircleUserRound, Clock } from "lucide-react";
import React, { useEffect, useMemo } from "react";
import moment from "moment";
import Markdown from "react-markdown";
import Prism from "prismjs";
import { useAppContext } from "@/context/AppContext";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import References from "./References";

const Message = ({ message, messages, index, processingData }) => {
	const { user } = useAppContext();
	const isUser = message.role === "user";

	// Memoize formatted time to avoid unnecessary recalculations
	const formattedTime = useMemo(() => {
		return moment(message.created_at).fromNow();
	}, [message.created_at]);

	useEffect(() => {
		// Only highlight if message is from assistant (contains code)
		if (!isUser && message.content) {
			Prism.highlightAll();
		}
	}, [message.content, isUser]);

	return (
		<div
			className={cn(
				"group flex items-start gap-6 my-6 w-full transition-all duration-200",
				isUser ? "flex-row-reverse justify-start" : "justify-start"
			)}
		>
			{/* Avatar */}
			<div
				className={cn(
					"flex items-center justify-center rounded-full shrink-0 transition-all",
					"size-10 ring-2 ring-offset-2 shadow-md",
					isUser
						? "bg-linear-to-br from-primary to-primary/80 text-primary-foreground ring-primary/20"
						: "bg-linear-to-br from-secondary to-secondary/80 text-secondary-foreground ring-secondary/20"
				)}
			>
				{isUser ? (
					<CircleUserRound className="size-5" />
				) : (
					<Bot className="size-5" />
				)}
			</div>

			{/* Message Content */}
			<Card
				className={cn(
					"max-w-2xl shadow-md hover:shadow-lg transition-all duration-200 border gap-0",
					isUser
						? "bg-linear-to-br from-primary/10 to-primary/5 border-primary/30 hover:border-primary/50"
						: "bg-linear-to-br from-secondary/30 to-background border-secondary/40 hover:border-secondary/60"
				)}
			>
				<CardContent className="pt-0">
					<div
						className={cn(
							"text-sm leading-relaxed",
							!isUser &&
								"reset-tw prose prose-sm max-w-none dark:prose-invert"
						)}
					>
						{isUser ? (
							<p className="whitespace-pre-wrap wrap-break-word">
								{message.content}
							</p>
						) : (
							<Markdown>{message.content}</Markdown>
						)}
					</div>

					{/* Show references - use message's docs or fall back to processingData for latest message */}
					{(() => {
						const docs =
							message.retrieved_documents ||
							(index === messages.length - 1 &&
								processingData?.documents) ||
							[];
						return docs.length > 0 ? (
							<References documents={docs} />
						) : null;
					})()}
					<div className="flex items-center gap-1 text-xs text-muted-foreground">
						<Clock className="size-3" />
						<span>{formattedTime}</span>
					</div>
				</CardContent>
			</Card>
		</div>
	);
};

export default Message;

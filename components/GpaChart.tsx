"use client"

import { LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer } from "recharts"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import type { GpaHistory } from "@/lib/studentProfileSchema"

interface GpaChartProps {
  gpaData: GpaHistory[]
}

export default function GpaChart({ gpaData }: GpaChartProps) {
  // Sort data by date_recorded to ensure correct trend display
  const sortedGpaData = [...gpaData].sort(
    (a, b) => new Date(a.date_recorded).getTime() - new Date(b.date_recorded).getTime(),
  )

  // Format date for display on X-axis
  const formatXAxis = (tickItem: string) => {
    const date = new Date(tickItem)
    return date.toLocaleDateString("en-US", { month: "short", year: "numeric" })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>GPA Trend</CardTitle>
        <CardDescription>Historical GPA over time.</CardDescription>
      </CardHeader>
      <CardContent>
        {sortedGpaData.length > 0 ? (
          <ChartContainer
            config={{
              gpa: {
                label: "GPA",
                color: "hsl(var(--chart-1))",
              },
            }}
            className="h-[300px] w-full"
          >
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={sortedGpaData}
                margin={{
                  top: 10,
                  right: 30,
                  left: 0,
                  bottom: 0,
                }}
              >
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="date_recorded"
                  tickFormatter={formatXAxis}
                  minTickGap={20}
                  angle={-45}
                  textAnchor="end"
                  height={60}
                />
                <YAxis domain={[0, 4]} tickCount={5} allowDecimals={true} tickFormatter={(value) => value.toFixed(1)} />
                <ChartTooltip cursor={false} content={<ChartTooltipContent />} />
                <Line
                  type="monotone"
                  dataKey="gpa"
                  stroke="var(--color-gpa)"
                  strokeWidth={2}
                  dot={{ r: 4 }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </ChartContainer>
        ) : (
          <div className="flex items-center justify-center h-[300px] text-muted-foreground">
            No GPA history available.
          </div>
        )}
      </CardContent>
    </Card>
  )
}

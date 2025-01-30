export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="relative pt-6 pb-16 sm:pb-24">
          <main className="mt-16">
            {children}
          </main>
        </div>
      </div>
    </div>
  );
}

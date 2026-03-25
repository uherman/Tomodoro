class Tomodoro < Formula
  desc "Terminal-based pomodoro timer with ASCII tomato art"
  homepage "https://github.com/uherman/tomodoro"
  url "RELEASE_URL_PLACEHOLDER"
  sha256 "SHA256_PLACEHOLDER"
  license "MIT"
  version "VERSION_PLACEHOLDER"

  depends_on :macos

  def install
    bin.install "tomodoro-macos" => "tomodoro"
  end

  test do
    assert_match "tomodoro", shell_output("#{bin}/tomodoro --help 2>&1", 1)
  end
end

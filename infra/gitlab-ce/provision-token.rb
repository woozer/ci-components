# Run with gitlab-rails runner inside this local GitLab container.
# The short-lived provisioning token is written to a private file, never stdout.
require 'securerandom'

user = User.find_by!(username: 'root')
raw_token = 'glpat-' + SecureRandom.alphanumeric(32)
token = user.personal_access_tokens.build(
  name: 'Local hello-world provisioning',
  scopes: ['api', 'write_repository', 'create_runner'],
  expires_at: 7.days.from_now.to_date
)
token.set_token(raw_token)
token.save!
File.open('/tmp/hello-world-provisioning-token', File::WRONLY | File::CREAT | File::TRUNC, 0600) do |file|
  file.write(raw_token)
end
puts 'Local provisioning token saved privately; expires in seven days.'
